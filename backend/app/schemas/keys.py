from pydantic import BaseModel

class ApiKeyCreate(BaseModel):
    provider: str
    api_key: str

class ApiKeyResponse(BaseModel):
    provider: str
    masked_key: str  # We only return "sk-...1234" to the frontend

    class Config:
        from_attributes = True