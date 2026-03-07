import os
from cryptography.fernet import Fernet
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Request, HTTPException, Security, Depends
import jwt

# Generate with `Fernet.generate_key().decode()` and put in .env
# Using a static fallback for development testing
FERNET_KEY = os.getenv("FERNET_KEY", b"vYF9Qv2X6M-h2iVzYw6x4jQ-l8bA4yD-J0A6V9r8N-k=")
cipher_suite = Fernet(FERNET_KEY)

# Simple API Token / JWT Mock Setup for Role-Based Access Requirement
SECRET_KEY = os.getenv("SECRET_KEY", "quicktrack-super-secret-key")
ALGORITHM = "HS256"
security = HTTPBearer()

def encrypt_data(data: str) -> str:
    """Encrypts raw text into Fernet token"""
    if not data:
        return ""
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_data(token: str) -> str:
    """Decrypts Fernet token back to raw text"""
    if not token:
        return ""
    try:
        return cipher_suite.decrypt(token.encode()).decode()
    except Exception:
        return "Decryption Failed"

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Mock JWT verification ensuring role-based access for Quick Track Accounting Dept.
    For local dev, pass Authorization: Bearer <any-string>
    """
    token = credentials.credentials
    if not token:
        raise HTTPException(status_code=401, detail="Invalid auth credentials")
    
    # In a real app, decode token, check 'role' == 'Accounting'
    # Mocking successful user retrieval here
    return {"user_id": 1, "username": "accounting_user", "role": "Accounting"}
