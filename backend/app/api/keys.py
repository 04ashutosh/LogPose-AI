from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.api.chat import get_current_user # Re-use the dependency
from app.models.models import User, ApiKey
from app.schemas.keys import ApiKeyCreate, ApiKeyResponse
from app.core.encryption import encrypt_api_key

router = APIRouter(prefix="/keys", tags=["API Keys"])

@router.get("", response_model=list[ApiKeyResponse])
async def get_keys(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiKey).filter(ApiKey.user_id == user.id))
    keys = result.scalars().all()
    
    # Mask keys before sending to frontend
    response = []
    for k in keys:
        # We decrypt just to find the length/suffix, then mask it
        from app.core.encryption import decrypt_api_key
        raw = decrypt_api_key(k.encrypted_key)
        masked = f"{raw[:3]}...{raw[-4:]}" if len(raw) > 10 else "***"
        response.append(ApiKeyResponse(provider=k.provider, masked_key=masked))
    return response

@router.post("", response_model=ApiKeyResponse)
async def set_key(key_in: ApiKeyCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Check if provider already exists
    result = await db.execute(select(ApiKey).filter(ApiKey.user_id == user.id, ApiKey.provider == key_in.provider))
    existing_key = result.scalars().first()
    
    encrypted = encrypt_api_key(key_in.api_key)
    
    if existing_key:
        existing_key.encrypted_key = encrypted
    else:
        new_key = ApiKey(user_id=user.id, provider=key_in.provider, encrypted_key=encrypted)
        db.add(new_key)
        
    await db.commit()
    masked = f"{key_in.api_key[:3]}...{key_in.api_key[-4:]}" if len(key_in.api_key) > 10 else "***"
    return ApiKeyResponse(provider=key_in.provider, masked_key=masked)