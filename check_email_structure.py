import pymongo

client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["email_response_system"]

emails = list(db.emails.find().limit(1))
if emails:
    email = emails[0]
    print("Email document structure:")
    for key in email.keys():
        print(f"  {key}: {type(email[key]).__name__}")
else:
    print("No emails found")
