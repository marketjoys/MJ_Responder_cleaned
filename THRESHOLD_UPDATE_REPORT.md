# Meeting Detection Threshold Update

## Changes Made

Reduced meeting detection and calendar event creation thresholds from **0.6/0.8** to **0.4** to make the calendar agent more sensitive to meeting requests.

---

## Updated Thresholds

### Before (Conservative)
- **Meeting Intent Processing**: Confidence >= **0.6** required
- **Calendar Event Auto-Creation**: Confidence >= **0.8** required
- **Needs Confirmation**: Confidence < **0.8**

### After (More Lenient)
- **Meeting Intent Processing**: Confidence >= **0.4** required ⬇️
- **Calendar Event Auto-Creation**: Confidence >= **0.4** required ⬇️
- **Needs Confirmation**: Confidence < **0.4** ⬇️

---

## Files Modified

### 1. `/app/backend/server.py`

**Line 2964** - Email processing workflow:
```python
# OLD: if meeting_detection.meeting_detected and meeting_detection.confidence_score >= 0.6:
# NEW:
if meeting_detection.meeting_detected and meeting_detection.confidence_score >= 0.4:
```

### 2. `/app/backend/calendar_agent.py`

**Line 387** - Meeting intent processing check:
```python
# OLD: meeting_detection.confidence_score < 0.6
# NEW:
meeting_detection.confidence_score < 0.4
```

**Line 103** - Needs confirmation threshold:
```python
# OLD: needs_confirmation=combined_detection['confidence'] < 0.8
# NEW:
needs_confirmation=combined_detection['confidence'] < 0.4
```

**Line 424** - Auto-create calendar event:
```python
# OLD: if meeting_detection.confidence_score >= 0.8 and not meeting_detection.needs_confirmation:
# NEW:
if meeting_detection.confidence_score >= 0.4 and not meeting_detection.needs_confirmation:
```

**Lines 186-188** - AI prompt confidence levels updated:
```python
# OLD:
# - High confidence (>0.8): Specific date, time, and clear meeting purpose
# - Medium confidence (0.6-0.8): Clear meeting intent with date OR time
# - Low confidence (0.3-0.6): Meeting keywords present but vague timing

# NEW:
- High confidence (>0.7): Specific date, time, and clear meeting purpose
- Medium confidence (0.4-0.7): Clear meeting intent with date OR time
- Low confidence (0.2-0.4): Meeting keywords present but vague timing
```

---

## Impact Analysis

### What This Means

1. **More Meetings Detected** ✅
   - Emails with ambiguous meeting language (confidence 0.4-0.6) will now be processed
   - Previously ignored meetings will now create meeting intents

2. **More Calendar Events Auto-Created** ✅
   - Events with confidence 0.4-0.8 will now be auto-created
   - Previously required manual confirmation

3. **Fewer Confirmation Requests** ⚠️
   - Only emails with confidence < 0.4 will require confirmation
   - Previously was < 0.8

### Examples of What Will Now Trigger

**Previously Ignored (0.4-0.6 confidence):**
- "Let's chat sometime next week"
- "We should catch up soon"
- "Can we discuss this over a call?"

**Previously Needed Confirmation (0.6-0.8 confidence):**
- "Meeting tomorrow afternoon?"
- "Call me when you're free"
- "Let's schedule something"

**Still Requires Confirmation (< 0.4 confidence):**
- "Thanks for your email"
- "Looking forward to hearing from you"
- Very ambiguous meeting hints

---

## Testing Recommendations

### Test Case 1: Low Confidence (0.4-0.5)
```
Subject: Quick Question
Body: Can we discuss this over a call sometime?
Expected: Meeting detected, event created, no confirmation needed
```

### Test Case 2: Medium Confidence (0.5-0.7)
```
Subject: Meeting Request
Body: Let's schedule a meeting next Tuesday afternoon
Expected: Meeting detected, event created, no confirmation needed
```

### Test Case 3: High Confidence (0.7+)
```
Subject: Meeting Tomorrow
Body: Can we meet tomorrow at 3:00 PM to discuss the project?
Expected: Meeting detected, event created with specific time, no confirmation needed
```

### Test Case 4: Very Low Confidence (< 0.4)
```
Subject: Thanks
Body: Thanks for the information. Talk soon!
Expected: Meeting not detected OR detected but needs confirmation
```

---

## Monitoring

### Check Meeting Detection

After sending test emails, monitor:

1. **Backend Logs**:
```bash
tail -f /var/log/supervisor/backend.out.log | grep -i "meeting detection"
```

Look for:
```
🔍 Parlant-Enhanced Meeting Detection: detected=True, confidence=0.45
```

2. **Database - Meeting Intents**:
```javascript
db.meeting_intents.find({user_id: "..."}).sort({created_at: -1})
```

3. **Database - Calendar Events**:
```javascript
db.calendar_events.find({user_id: "..."}).sort({created_at: -1})
```

### Expected Log Patterns

**Confidence 0.4-0.6 (Now Processed)**:
```
🔍 Parlant-Enhanced Meeting Detection: detected=True, confidence=0.45
📅 Parlant-Enhanced Calendar Action: <meeting_intent_id>
Successfully created calendar event <event_id>
```

**Confidence < 0.4 (Needs Confirmation)**:
```
🔍 Parlant-Enhanced Meeting Detection: detected=True, confidence=0.35
📅 Meeting detected but confidence too low (0.35) - applying clarification guidelines
```

---

## Rollback Plan

If the new threshold causes too many false positives, revert by changing:

1. In `server.py` line 2964: `0.4` → `0.6`
2. In `calendar_agent.py` line 387: `0.4` → `0.6`
3. In `calendar_agent.py` line 103: `0.4` → `0.8`
4. In `calendar_agent.py` line 424: `0.4` → `0.8`

Then restart backend:
```bash
sudo supervisorctl restart backend
```

---

## Best Practices

### Recommended Approach

1. **Start Testing**: Send emails with varying meeting intent clarity
2. **Monitor Results**: Check how many meetings are detected
3. **Adjust if Needed**: If too many false positives, increase threshold to 0.5
4. **Fine-tune**: Find the sweet spot between 0.4-0.6 based on your use case

### Threshold Guidelines

- **0.3**: Very aggressive - May create events for casual mentions
- **0.4**: Moderate-aggressive - Good balance (current setting)
- **0.5**: Balanced - Catches most clear meetings
- **0.6**: Conservative - Only clear meeting requests (previous setting)
- **0.8**: Very conservative - Only explicit meetings with date/time

---

## Status

- ✅ Thresholds updated from 0.6/0.8 to 0.4
- ✅ Backend restarted successfully
- ✅ All services running
- ✅ Ready for testing with new threshold

**Date**: 2025-10-30  
**Updated By**: Calendar Agent Enhancement  
**Status**: Active  
