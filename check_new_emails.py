#!/usr/bin/env python3
import imaplib
import ssl
import email
import re
from email.header import decode_header
from datetime import datetime, timedelta

# Gmail account details
email_account = "rohushanshinde@gmail.com"
password = "pajbdmcpcegppguz"
imap_server = "imap.gmail.com"
imap_port = 993

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
    print(f"🔍 Checking for emails from samhere@gmail.com in {email_account}...")
    
    # Create SSL context and connect
    context = ssl.create_default_context()
    imap = imaplib.IMAP4_SSL(imap_server, imap_port, ssl_context=context)
    
    # Login and select INBOX
    imap.login(email_account, password)
    imap.select('INBOX')
    
    # Search for emails from samhere@gmail.com
    print("🔎 Searching for emails from samhere@gmail.com...")
    typ, msg_ids = imap.search(None, 'FROM', 'samhere@gmail.com')
    
    if typ == 'OK' and msg_ids[0]:
        email_ids = msg_ids[0].split()
        print(f"📧 Found {len(email_ids)} emails from samhere@gmail.com")
        
        # Check the most recent one
        if email_ids:
            latest_id = email_ids[-1]
            typ, msg_data = imap.fetch(latest_id, '(RFC822.HEADER UID)')
            if typ == 'OK' and msg_data[0]:
                email_message = email.message_from_bytes(msg_data[0][1])
                subject = decode_header_value(email_message.get('Subject', ''))
                date = email_message.get('Date', '')
                
                # Get UID from the response
                uid_info = msg_data[1]
                if isinstance(uid_info, bytes):
                    uid_str = uid_info.decode()
                    # Extract UID from string like "UID 488)"
                    import re
                    uid_match = re.search(r'UID (\d+)', uid_str)
                    if uid_match:
                        email_uid = int(uid_match.group(1))
                        print(f"  📍 Latest email from samhere@gmail.com:")
                        print(f"      Subject: {subject}")
                        print(f"      Date: {date}")
                        print(f"      UID: {email_uid}")
                        
                        if email_uid > 487:
                            print(f"  🎯 THIS EMAIL IS NEWER than last processed UID (487)!")
                            print(f"  ⚠️  System should have detected this email!")
                        else:
                            print(f"  ℹ️  This email is older than last processed UID (487)")
    else:
        print("📭 No emails found from samhere@gmail.com")
    
    # Also search for recent emails (last hour)
    print(f"\n🕐 Checking for ANY emails in the last 2 hours...")
    recent_time = (datetime.now() - timedelta(hours=2)).strftime("%d-%b-%Y")
    typ, msg_ids = imap.search(None, f'SINCE {recent_time}')
    
    if typ == 'OK' and msg_ids[0]:
        recent_email_ids = msg_ids[0].split()
        print(f"📧 Found {len(recent_email_ids)} recent emails")
        
        # Check last few
        for email_id in recent_email_ids[-3:]:  # Last 3 emails
            typ, msg_data = imap.fetch(email_id, '(RFC822.HEADER UID)')
            if typ == 'OK' and msg_data[0]:
                email_message = email.message_from_bytes(msg_data[0][1])
                subject = decode_header_value(email_message.get('Subject', ''))
                sender = decode_header_value(email_message.get('From', ''))
                date = email_message.get('Date', '')
                
                # Get UID
                uid_info = msg_data[1]
                if isinstance(uid_info, bytes):
                    uid_str = uid_info.decode()
                    uid_match = re.search(r'UID (\d+)', uid_str)
                    if uid_match:
                        email_uid = int(uid_match.group(1))
                        print(f"  📍 UID {email_uid}: From {sender}")
                        print(f"      Subject: {subject}")
                        if 'samhere' in sender.lower():
                            print(f"      🎯 THIS IS FROM samhere@gmail.com!")
    
    # Close connection
    imap.close()
    imap.logout()
    print("✅ Search completed")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()