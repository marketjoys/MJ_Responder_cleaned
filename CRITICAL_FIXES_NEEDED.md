# Critical Issues Found and Fixes Needed

## Issue 1: Auto-Send Not Working - Emails Stuck in ready_to_send/needs_redraft

### Problem:
- Emails are processed to "ready_to_send" status but never actually sent
- The auto_send_email_workflow is triggered but might not be executing properly
- No periodic service checking for stuck emails

### Root Cause:
In `server.py` line 3088, auto-send is queued via RQ but:
1. If RQ job fails silently, email stays stuck
2. No fallback mechanism
3. No periodic cleanup of stuck emails

### Solution:
1. Add periodic task to process stuck "ready_to_send" emails
2. Add better error handling in auto_send_email_workflow
3. Add timeout and retry logic

---

## Issue 2: Thread Handling - Emails Not Sent in Same Thread

### Problem:
- Reply emails are not maintaining proper threading
- Missing or incorrect In-Reply-To and References headers

### Root Cause:
In `server.py` auto_send_email function (lines 2718-2813):
- Thread headers (in_reply_to, references) are passed but may not be populated correctly from email_doc
- Need to verify email_doc contains message_id and references fields

### Solution:
1. Ensure email_doc stores message_id, in_reply_to, and references when parsing incoming emails
2. Pass correct threading headers when sending replies
3. Verify OAuth email sending (Google/Microsoft) uses threading headers

---

## Issue 3: Calendar Events Not Created Despite Meeting Detection

### Problem:
- Meeting intents detected successfully
- Calendar events not visible in calendar_events collection
- Events may be created in external calendar (Google) but not stored in DB

### Root Cause:
In `calendar_agent.py` _create_calendar_event (lines 459-516):
- Events are created via calendar_service.create_event()
- BUT: There's no code to store the created event in calendar_events collection
- Only stores in meeting_intents collection

### Solution:
1. After creating event externally, store it in calendar_events collection
2. Include all required fields: external_event_id, start_time, end_time, title, meeting_intent_id, user_id, etc.

---

## Issue 4: Processing Old Emails - UID Tracking Not Working on First Connect

### Problem:
- Agent processes ALL emails including old ones
- Should only process emails received AFTER account connection
- last_uid not set correctly on first connection

### Root Cause:
In `email_services.py` fetch_new_emails (lines 175-191):
- When last_uid is 0 (first time), it sets last_uid to latest UID
- BUT then returns empty array, so first run processes nothing (GOOD)
- HOWEVER: If account is deleted and re-added, last_uid might reset incorrectly
- Also: When account is first created, last_uid is set to 0 instead of current latest UID

### Solution:
1. When creating new email account, immediately fetch latest UID and set it as last_uid
2. Add "connected_at" timestamp to track when account was added
3. Only process emails with received_at > connected_at
4. Store last_uid at account creation time, not on first poll

---

## Priority Order:

1. **CRITICAL**: Issue 4 - UID tracking (prevents spam of old emails)
2. **HIGH**: Issue 1 - Auto-send stuck emails (core functionality)
3. **HIGH**: Issue 3 - Calendar events not stored in DB (data integrity)
4. **MEDIUM**: Issue 2 - Thread handling (user experience)

