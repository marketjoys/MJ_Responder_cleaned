import pymongo

client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["email_response_system"]

# Update all documents to have 'id' field matching '_id'
result = db.emails.update_many(
    {},
    [{"$set": {"id": "$_id"}}]
)

print(f"Updated {result.modified_count} emails with 'id' field")

# Update all other collections too
collections = ['email_accounts', 'users', 'intents', 'knowledge_base', 'oauth_tokens', 'calendar_providers']
for coll_name in collections:
    result = db[coll_name].update_many(
        {},
        [{"$set": {"id": "$_id"}}]
    )
    print(f"Updated {result.modified_count} {coll_name} documents with 'id' field")

