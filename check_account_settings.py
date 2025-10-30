import pymongo

client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["email_response_system"]

account = db.email_accounts.find_one({"email": "amits.joys@gmail.com"})
if account:
    print("Email Account Settings:")
    print(f"  Email: {account.get('email')}")
    print(f"  Auto Send: {account.get('auto_send')}")
    print(f"  Enable Follow-ups: {account.get('enable_follow_ups')}")
    print(f"  Is Active: {account.get('is_active')}")
    
    print("\n📧 Ready to Send Emails:")
    emails = list(db.emails.find({"status": "ready_to_send", "user_id": account['user_id']}))
    for email in emails:
        print(f"  - {email['subject']} (ID: {email['_id']})")
else:
    print("Account not found")
