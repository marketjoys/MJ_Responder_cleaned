from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import os
from motor.motor_asyncio import AsyncIOMotorClient

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Load environment variables
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
security = HTTPBearer()

# MongoDB connection (reuse from server.py)
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = ""

class UserLogin(BaseModel):
    email: str
    password: str

class User(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool = True
    email_quota: int = 100  # Default monthly quota
    emails_used: int = 0
    quota_reset_date: datetime
    created_at: datetime
    timezone: str = "UTC"

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

class TokenData(BaseModel):
    email: Optional[str] = None

# Utility functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    # Truncate password to 72 bytes for bcrypt compatibility
    password_bytes = password.encode('utf-8')[:72]
    truncated_password = password_bytes.decode('utf-8', errors='ignore')
    return pwd_context.hash(truncated_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_user_by_email(email: str) -> Optional[Dict]:
    """Get user by email from database"""
    user = await db.users.find_one({"email": email})
    return user

async def get_user_by_id(user_id: str) -> Optional[Dict]:
    """Get user by ID from database"""
    user = await db.users.find_one({"id": user_id})
    return user

async def authenticate_user(email: str, password: str) -> Optional[Dict]:
    """Authenticate user with email and password"""
    user = await get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_email(email=token_data.email)
    if user is None:
        raise credentials_exception
    
    return User(**user)

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def check_email_quota(user: User) -> bool:
    """Check if user has remaining email quota"""
    now = datetime.utcnow()
    
    # Reset quota if month has passed
    if now >= user.quota_reset_date:
        await reset_user_quota(user.id)
        return True
    
    return user.emails_used < user.email_quota

async def increment_email_usage(user_id: str):
    """Increment user's email usage count"""
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"emails_used": 1}}
    )

async def reset_user_quota(user_id: str):
    """Reset user's email quota for new month"""
    next_month = datetime.utcnow().replace(day=1) + timedelta(days=32)
    next_month = next_month.replace(day=1)
    
    await db.users.update_one(
        {"id": user_id},
        {
            "$set": {
                "emails_used": 0,
                "quota_reset_date": next_month
            }
        }
    )

async def update_user_quota(user_id: str, new_quota: int):
    """Update user's email quota (for upgrades)"""
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"email_quota": new_quota}}
    )

async def get_user_quota_info(user_id: str) -> Dict[str, Any]:
    """Get user's quota information"""
    user = await get_user_by_id(user_id)
    if not user:
        return {}
    
    remaining = max(0, user["email_quota"] - user["emails_used"])
    days_until_reset = (user["quota_reset_date"] - datetime.utcnow()).days
    
    return {
        "email_quota": user["email_quota"],
        "emails_used": user["emails_used"],
        "emails_remaining": remaining,
        "quota_reset_date": user["quota_reset_date"],
        "days_until_reset": max(0, days_until_reset),
        "quota_percentage_used": (user["emails_used"] / user["email_quota"]) * 100 if user["email_quota"] > 0 else 0
    }