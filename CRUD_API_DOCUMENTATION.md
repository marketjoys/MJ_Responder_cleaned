# Complete CRUD API Documentation

## 🎯 INTENTS Management

### Create Intent
```http
POST /api/intents
Content-Type: application/json

{
  "name": "Customer Support",
  "description": "Customer service and support requests",
  "examples": ["I need help", "Support ticket", "Technical issue"],
  "system_prompt": "Handle support requests professionally",
  "confidence_threshold": 0.75,
  "follow_up_hours": 24,
  "is_meeting_related": false
}
```

### Get All Intents
```http
GET /api/intents
```

### Get Specific Intent
```http
GET /api/intents/{intent_id}
```

### Update Intent
```http
PUT /api/intents/{intent_id}
Content-Type: application/json

{
  "name": "Updated Customer Support",
  "description": "Updated description triggers embedding regeneration",
  "examples": ["Updated examples", "New help request"],
  "system_prompt": "Updated system prompt",
  "confidence_threshold": 0.8,
  "follow_up_hours": 12,
  "is_meeting_related": false
}
```

### Delete Intent
```http
DELETE /api/intents/{intent_id}
```

---

## 📚 KNOWLEDGE BASE Management

### Create Knowledge Base Entry
```http
POST /api/knowledge-base
Content-Type: application/json

{
  "title": "Product Information",
  "content": "Detailed product information and specifications...",
  "tags": ["product", "features", "specs"]
}
```

### Get All Knowledge Base Entries
```http
GET /api/knowledge-base
```

### Get Specific Knowledge Base Entry
```http
GET /api/knowledge-base/{kb_id}
```

### Update Knowledge Base Entry
```http
PUT /api/knowledge-base/{kb_id}
Content-Type: application/json

{
  "title": "Updated Product Information",
  "content": "Updated content triggers embedding regeneration...",
  "tags": ["product", "features", "updated"]
}
```

### Delete Knowledge Base Entry
```http
DELETE /api/knowledge-base/{kb_id}
```

---

## 📧 EMAIL ACCOUNTS Management

### Create Email Account
```http
POST /api/email-accounts
Content-Type: application/json

{
  "name": "Business Email",
  "email": "business@company.com",
  "provider": "gmail",
  "username": "business@company.com",
  "password": "app-specific-password",
  "persona": "Professional business representative",
  "signature": "Best regards,\nBusiness Team",
  "auto_send": true
}
```

### Get All Email Accounts
```http
GET /api/email-accounts
```
*Note: Passwords are masked as "***" in responses*

### Get Specific Email Account
```http
GET /api/email-accounts/{account_id}
```

### Update Email Account
```http
PUT /api/email-accounts/{account_id}
Content-Type: application/json

{
  "name": "Updated Business Email",
  "email": "updated@company.com",
  "provider": "outlook",
  "username": "updated@company.com",
  "password": "new-password",
  "persona": "Updated persona",
  "signature": "Updated signature",
  "auto_send": false
}
```
*Note: Connection settings changes force reconnection*

### Delete Email Account
```http
DELETE /api/email-accounts/{account_id}
```
*Note: Automatically cleans up polling connections*

### Toggle Account Status
```http
PUT /api/email-accounts/{account_id}/toggle
```
*Activates/deactivates account and manages polling*

---

## 🔄 INDIVIDUAL POLLING CONTROL

### Start Polling for Account
```http
POST /api/email-accounts/{account_id}/polling
Content-Type: application/json

{
  "action": "start"
}
```

### Stop Polling for Account
```http
POST /api/email-accounts/{account_id}/polling
Content-Type: application/json

{
  "action": "stop"
}
```

### Get Account Polling Status
```http
POST /api/email-accounts/{account_id}/polling
Content-Type: application/json

{
  "action": "status"
}
```

**Response:**
```json
{
  "account_id": "uuid",
  "email": "user@domain.com",
  "polling_active": true,
  "has_connection": true,
  "last_polled": "2025-08-14T10:30:00Z",
  "last_uid": 450
}
```

### Get All Accounts Polling Status
```http
GET /api/polling/accounts-status
```

**Response:**
```json
{
  "polling_service_running": true,
  "total_accounts": 3,
  "active_accounts": 2,
  "connected_accounts": 2,
  "accounts": [
    {
      "account_id": "uuid1",
      "email": "user1@domain.com",
      "name": "Account 1",
      "polling_active": true,
      "has_connection": true,
      "last_polled": "2025-08-14T10:30:00Z",
      "last_uid": 450
    }
  ]
}
```

---

## 🔍 SYSTEM STATUS Endpoints

### Dashboard Statistics
```http
GET /api/dashboard/stats
```

### Global Polling Status
```http
GET /api/polling/status
```

### Global Polling Control
```http
POST /api/polling/control
Content-Type: application/json

{
  "action": "start|stop|status"
}
```

---

## ⚡ KEY FEATURES

### Automatic Embedding Generation
- **Intents**: Embeddings generated from description + examples
- **Knowledge Base**: Embeddings generated from content
- **Auto-Regeneration**: Embeddings updated when content changes

### Connection Management
- **Connection Pooling**: Reuses IMAP connections efficiently
- **Health Checks**: Validates connections before use
- **Auto-Cleanup**: Removes connections when accounts deleted/modified
- **Individual Control**: Start/stop polling per account

### Data Integrity
- **Validation**: Proper error handling for invalid IDs
- **Security**: Passwords masked in API responses
- **Consistency**: Updates maintain referential integrity

### Error Responses
All endpoints return appropriate HTTP status codes:
- **200**: Success
- **201**: Created
- **404**: Not Found
- **400**: Bad Request
- **500**: Internal Server Error

---

## 🎯 USAGE EXAMPLES

### Complete CRUD Workflow

1. **Create** a new intent
2. **Read** the created intent to verify
3. **Update** the intent (triggers embedding regeneration)
4. **Delete** the intent when no longer needed

### Individual Account Management

1. **Create** email account
2. **Start polling** for specific account
3. **Monitor status** via polling endpoints
4. **Stop polling** when needed
5. **Update account** settings (auto-reconnects)

### Knowledge Base Management

1. **Add** business-specific knowledge
2. **Update** content (auto-regenerates embeddings)
3. **Query** via AI classification system
4. **Remove** outdated information

All operations maintain system integrity and provide detailed feedback for monitoring and debugging.