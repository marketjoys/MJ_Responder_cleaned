import pymongo
from datetime import datetime

client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["email_response_system"]

# Get all emails
emails = list(db.emails.find())

for email in emails:
    update_data = {}
    
    # Map sender_email to sender
    if 'sender_email' in email and 'sender' not in email:
        update_data['sender'] = email['sender_email']
    
    # Set recipient (user's email)
    if 'recipient' not in email:
        update_data['recipient'] = 'amits.joys@gmail.com'
    
    # Rename email_account_id to account_id
    if 'email_account_id' in email and 'account_id' not in email:
        update_data['account_id'] = email['email_account_id']
    
    # Ensure body_html exists
    if 'body_html' not in email:
        update_data['body_html'] = f"<p>{email.get('body', '')}</p>"
    
    # Set defaults for other fields
    if 'status' not in email:
        update_data['status'] = 'new'
    if 'is_read' not in email:
        update_data['is_read'] = False
    if 'intents' not in email:
        update_data['intents'] = []
    if 'draft' not in email:
        update_data['draft'] = ''
    if 'draft_html' not in email:
        update_data['draft_html'] = ''
    
    if update_data:
        db.emails.update_one(
            {"_id": email['_id']},
            {"$set": update_data}
        )
        print(f"Updated email {email['_id']}: {email.get('subject', 'N/A')[:40]}")

print("\n✅ All emails updated")
