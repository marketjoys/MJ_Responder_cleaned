import pymongo
from datetime import datetime, timedelta

client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["email_response_system"]

# Update user with missing fields
result = db.users.update_one(
    {"email": "amits.joys@gmail.com"},
    {"$set": {
        "email_quota": 100,
        "emails_used": 0,
        "timezone": "UTC",
        "created_at": datetime.utcnow()
    }}
)

print(f"✅ Updated user with quota fields (modified: {result.modified_count})")

# Verify
user = db.users.find_one({"email": "amits.joys@gmail.com"})
print(f"\nUser fields:")
for key in ['email', 'email_quota', 'emails_used', 'timezone', 'is_active']:
    print(f"  {key}: {user.get(key)}")

