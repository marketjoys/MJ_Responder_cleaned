# OAuth Setup Guide for Email Automation System

## Current Configuration

### Domain
**Application URL:** `https://calendar-agent-fix.preview.emergentagent.com`

### OAuth Redirect URIs
- **Google OAuth:** `https://calendar-agent-fix.preview.emergentagent.com/oauth/google/callback`
- **Microsoft OAuth:** `https://calendar-agent-fix.preview.emergentagent.com/oauth/microsoft/callback`

---

## Microsoft Azure App Registration Setup

### Step 1: Update Redirect URI in Azure Portal

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to **Azure Active Directory** → **App registrations**
3. Find your app: **Client ID:** `41370f61-416c-4f33-ae52-70468b1c1927`
4. Click on **Authentication** in the left sidebar
5. Under **Platform configurations** → **Web**, add/update the redirect URI:
   ```
   https://calendar-agent-fix.preview.emergentagent.com/oauth/microsoft/callback
   ```
6. Remove any old redirect URIs (like `dev-restart-setup.preview.emergentagent.com`)
7. Click **Save**

### Step 2: Verify API Permissions

Ensure the following permissions are granted:
- ✅ Mail.Read
- ✅ Mail.Send
- ✅ Mail.ReadWrite
- ✅ Calendars.Read
- ✅ Calendars.ReadWrite
- ✅ User.Read
- ✅ offline_access

If any are missing:
1. Go to **API permissions** tab
2. Click **Add a permission** → **Microsoft Graph** → **Delegated permissions**
3. Search and add the missing permissions
4. Click **Grant admin consent** (if you have admin rights)

### Step 3: Verify Tenant Configuration

- **Tenant ID:** `cf93f5c7-89b8-4808-b550-b61a85422828`
- **Supported account types:** Should allow organizational accounts
- **Client Secret:** Ensure it hasn't expired (check **Certificates & secrets** tab)

---

## Google OAuth Setup

### Step 1: Update Redirect URI in Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services** → **Credentials**
3. Find your OAuth 2.0 Client: **Client ID:** `691413402120-tlhotgqvkpevgvaaaff8h1r8t7lk0k9i.apps.googleusercontent.com`
4. Click to edit the OAuth client
5. Under **Authorized redirect URIs**, add/update:
   ```
   https://calendar-agent-fix.preview.emergentagent.com/oauth/google/callback
   ```
6. Remove any old redirect URIs
7. Click **Save**

### Step 2: Verify Scopes

Ensure the following scopes are enabled:
- ✅ Gmail API (https://www.googleapis.com/auth/gmail.readonly, gmail.send, gmail.modify)
- ✅ Calendar API (https://www.googleapis.com/auth/calendar, calendar.events)
- ✅ User Info (email, profile)

---

## Testing OAuth Flow

### For Microsoft Outlook

1. Login to the app as: `amits.joys@gmail.com` (Password: `Ij@123`)
2. Navigate to **Email Accounts** section
3. Click **Add OAuth Account** button
4. Select **Microsoft/Outlook** provider
5. Enter your Outlook email: `amits.joys@outlook.com`
6. Click **Authorize**
7. You'll be redirected to Microsoft login
8. Login and grant permissions
9. You should be redirected back to the app
10. Verify the account appears in the list with OAuth badge

### For Google Gmail

1. Follow similar steps but select **Google/Gmail** provider
2. Enter your Gmail address
3. Complete Google OAuth flow
4. Grant permissions for Gmail and Calendar
5. Verify successful connection

---

## Troubleshooting

### "Invalid or expired OAuth state" Error
- This happens if:
  - The redirect URI doesn't match exactly in Azure/Google console
  - The OAuth flow took longer than 10 minutes
  - Browser cookies are blocked
- **Solution:** Update redirect URIs and try again

### "Authorization failed" Error
- Check that redirect URIs match exactly (including https://)
- Verify client secrets haven't expired
- Ensure API permissions are granted
- Check browser console for detailed error messages

### "401 Unauthorized" During Polling
- Token might be expired or revoked
- Re-authorize the account through the OAuth flow
- Check that the refresh token is present in the database

### Account Shows as "Paused" or "Inactive"
- Use the toggle button (Play/Pause icon) to activate
- If toggle doesn't work, check browser console for errors
- Verify the account has `is_active: true` in database

---

## Database Verification

### Check OAuth Tokens

```bash
# Microsoft tokens
mongosh test_database --eval "db.oauth_tokens_microsoft.find().pretty()"

# Google tokens
mongosh test_database --eval "db.oauth_tokens.find().pretty()"
```

### Check Email Accounts

```bash
mongosh test_database --eval "db.email_accounts.find({auth_type: 'oauth'}).pretty()"
```

### Verify Token Linking

Ensure each OAuth email account has:
- `auth_type: "oauth"`
- `use_oauth: true`
- `oauth_token_id: "<valid-token-id>"`
- `oauth_email: "<matching-email>"`
- `is_active: true`

---

## Current Environment Variables

Located in `/app/backend/.env`:

```env
# Microsoft OAuth
MICROSOFT_CLIENT_ID="41370f61-416c-4f33-ae52-70468b1c1927"
MICROSOFT_CLIENT_SECRET="ZA-8Q~HalBnl3OkxnxyrDjqnzDheedqc-Z6fvc74"
MICROSOFT_TENANT_ID="cf93f5c7-89b8-4808-b550-b61a85422828"
MICROSOFT_REDIRECT_URI="https://calendar-agent-fix.preview.emergentagent.com/oauth/microsoft/callback"

# Google OAuth
GOOGLE_CLIENT_ID="691413402120-tlhotgqvkpevgvaaaff8h1r8t7lk0k9i.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="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"
GOOGLE_REDIRECT_URI="https://calendar-agent-fix.preview.emergentagent.com/oauth/google/callback"
```

---

## Support

If you continue to experience issues:
1. Check backend logs: `tail -f /var/log/supervisor/backend.err.log`
2. Check frontend console in browser DevTools
3. Verify all services are running: `sudo supervisorctl status`
4. Ensure Redis is operational: `redis-cli ping` (should return PONG)
