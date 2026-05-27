import base64
from cryptography.fernet import Fernet
from app.core.config import settings

# Fernet requires a 32-byte url-safe base64-encoded key
def get_cipher():
    # Pad the key if it's not exactly 32 bytes for the prototype
    key = settings.ENCRYPTION_KEY.encode('utf-8')
    key = base64.urlsafe_b64encode(key.ljust(32)[:32])
    return Fernet(key)

def encrypt_api_key(plain_text: str) -> str:
    cipher = get_cipher()
    return cipher.encrypt(plain_text.encode('utf-8')).decode('utf-8')

def decrypt_api_key(encrypted_text: str) -> str:
    cipher = get_cipher()
    return cipher.decrypt(encrypted_text.encode('utf-8')).decode('utf-8')