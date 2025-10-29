#!/usr/bin/env python3
"""
Script to create a user account in the database
"""
import os
import uuid
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
import bcrypt

load_dotenv()

def get_password_hash(password: str) -> str:
    """Hash a password with bcrypt 72-byte limit handling"""
    # Encode the password as UTF-8 and truncate to 72 bytes
    password_bytes = password.encode('utf-8')[:72]
    
    # Decode back to string, handling potential incomplete UTF-8 at the end
    try:
        truncated_password = password_bytes.decode('utf-8')
    except UnicodeDecodeError:
        # If we cut in the middle of a multi-byte character, truncate further
        for i in range(1, 5):  # UTF-8 characters can be up to 4 bytes
            try:
                truncated_password = password_bytes[:-i].decode('utf-8')
                break
            except UnicodeDecodeError:
                continue
        else:
            # Fallback to first 70 bytes if all else fails
            truncated_password = password_bytes[:70].decode('utf-8', errors='ignore')
    
    # Use bcrypt directly with 12 rounds
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(truncated_password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def create_user(email: str, password: str):
    """Create a user in the database"""
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.getenv("DB_NAME", "test_database")
    
    client = MongoClient(mongo_url)
    db = client[db_name]
    
    # Check if user already exists
    existing_user = db.users.find_one({"email": email})
    if existing_user:
        print(f"✅ User {email} already exists with ID: {existing_user.get('user_id')}")
        return existing_user.get('user_id')
    
    # Create new user
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(password)
    
    user_data = {
        "user_id": user_id,
        "email": email,
        "password_hash": hashed_password,
        "created_at": datetime.utcnow(),
        "is_active": True,
        "oauth_accounts": []
    }
    
    db.users.insert_one(user_data)
    print(f"✅ Created user {email} with ID: {user_id}")
    return user_id

if __name__ == "__main__":
    # Create the user
    user_id = create_user("amits.joys@gmail.com", "ij@123")
    print(f"\n📧 User created successfully!")
    print(f"   Email: amits.joys@gmail.com")
    print(f"   Password: ij@123")
    print(f"   User ID: {user_id}")
