#!/usr/bin/env python3
import imaplib
import ssl
import email
from email.header import decode_header
from datetime import datetime, timedelta

# Gmail account details
email_account = "rohushanshinde@gmail.com"
password = "pajbdmcpcegppguz"
imap_server = "imap.gmail.com"
imap_port = 993
current_last_uid = 791  # Updated to current system value

def decode_header_value(header_value):
    if not header_value:
        return ''
    try:
        decoded_parts = decode_header(header_value)
        decoded_string = ''
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                if encoding:
                    decoded_string += part.decode(encoding)
                else:
                    decoded_string += part.decode('utf-8', errors='ignore')
            else:
                decoded_string += part
        return decoded_string
    except:
        return header_value

try:
    print(f"🔍 Testing IMAP connection for new emails...")
    print(f"📊 Current system last UID: {current_last_uid}")
    
    # Create SSL context and connect
    context = ssl.create_default_context()
    imap = imaplib.IMAP4_SSL(imap_server, imap_port, ssl_context=context)
    
    # Login and select INBOX
    imap.login(email_account, password)
    imap.select('INBOX')
    print("✅ IMAP connection successful")
    
    # Get all UIDs to see the current state
    typ, all_msg_ids = imap.uid('search', None, 'ALL')
    if typ == 'OK' and all_msg_ids[0]:
        all_uids = [int(uid.decode()) for uid in all_msg_ids[0].split() if uid]
        latest_uid = max(all_uids) if all_uids else 0
        print(f"📊 Current latest UID in inbox: {latest_uid}")
        
        if latest_uid > current_last_uid:
            print(f"🎯 NEW EMAILS DETECTED! UIDs {current_last_uid + 1} to {latest_uid}")
            
            # Check emails after our last UID
            typ, new_msg_ids = imap.uid('search', None, f'UID {current_last_uid + 1}:*')
            if typ == 'OK' and new_msg_ids[0]:
                new_uids = [int(uid.decode()) for uid in new_msg_ids[0].split() if uid]
                print(f"📧 Found {len(new_uids)} new emails: UIDs {new_uids}")
                
                # Check each new email
                for uid in new_uids[-5:]:  # Check last 5 new emails
                    print(f"\n📧 Checking UID {uid}:")
                    typ, msg_data = imap.uid('fetch', str(uid), '(RFC822.HEADER)')
                    if typ == 'OK' and msg_data[0]:
                        email_message = email.message_from_bytes(msg_data[0][1])
                        subject = decode_header_value(email_message.get('Subject', ''))
                        sender = decode_header_value(email_message.get('From', ''))
                        date = email_message.get('Date', '')
                        
                        print(f"  📩 From: {sender}")
                        print(f"  📰 Subject: {subject}")
                        print(f"  📅 Date: {date}")
                        
                        if 'samhere' in sender.lower():
                            print(f"  🎯 *** FOUND EMAIL FROM SAMHERE! ***")
            else:
                print("❌ No new emails found in UID search")
        else:
            print(f"ℹ️  No new emails. Latest UID {latest_uid} <= current last UID {current_last_uid}")
    
    # Also search specifically for emails from samhere in the last few hours
    print(f"\n🔎 Searching specifically for emails from samhere.joy@gmail.com...")
    typ, msg_ids = imap.search(None, 'FROM', 'samhere.joy@gmail.com')
    
    if typ == 'OK' and msg_ids[0]:
        email_ids = [int(id.decode()) for id in msg_ids[0].split() if id]
        print(f"📧 Found {len(email_ids)} total emails from samhere.joy@gmail.com")
        
        # Check the most recent ones with UIDs
        for email_id in email_ids[-3:]:  # Last 3 emails
            typ, msg_data = imap.fetch(str(email_id), '(RFC822.HEADER UID)')
            if typ == 'OK' and msg_data:
                email_message = email.message_from_bytes(msg_data[0][1])
                subject = decode_header_value(email_message.get('Subject', ''))
                date = email_message.get('Date', '')
                
                # Extract UID from the response
                if len(msg_data) > 1 and isinstance(msg_data[1], bytes):
                    uid_str = msg_data[1].decode()
                    import re
                    uid_match = re.search(r'UID (\d+)', uid_str)
                    if uid_match:
                        email_uid = int(uid_match.group(1))
                        print(f"  📍 Email ID {email_id}, UID {email_uid}: {subject}")
                        print(f"      Date: {date}")
                        
                        if email_uid > current_last_uid:
                            print(f"      🎯 *** THIS EMAIL IS NEWER than system last UID {current_last_uid}! ***")
                            print(f"      ⚠️  System should have detected this!")
                        else:
                            print(f"      ℹ️  This email UID {email_uid} <= system last UID {current_last_uid}")
    else:
        print("📭 No emails found from samhere.joy@gmail.com")
    
    # Close connection
    imap.close()
    imap.logout()
    print("\n✅ IMAP debugging completed")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()