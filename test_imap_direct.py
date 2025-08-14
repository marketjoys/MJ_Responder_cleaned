#!/usr/bin/env python3
import imaplib
import ssl
import email
from email.header import decode_header

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
    print(f"🔍 Testing direct IMAP connection to {email_account}...")
    
    # Create SSL context and connect
    context = ssl.create_default_context()
    imap = imaplib.IMAP4_SSL(imap_server, imap_port, ssl_context=context)
    
    # Login
    print("🔐 Attempting login...")
    imap.login(email_account, password)
    print("✅ Login successful!")
    
    # Select INBOX
    imap.select('INBOX')
    print("📬 Selected INBOX")
    
    # Get total emails
    typ, all_msg_ids = imap.search(None, 'ALL')
    if typ == 'OK' and all_msg_ids[0]:
        all_uids = [uid for uid in all_msg_ids[0].split() if uid]
        print(f"📊 Total emails in inbox: {len(all_uids)}")
        if all_uids:
            latest_uid = int(all_uids[-1].decode())
            print(f"🔢 Latest UID in inbox: {latest_uid}")
            print(f"🔢 System thinks last UID is: 784")
            
            if latest_uid > 784:
                print(f"⚠️  NEW EMAILS DETECTED! UIDs {785} to {latest_uid}")
                
                # Check recent emails (last 5)
                recent_uids = all_uids[-5:] if len(all_uids) >= 5 else all_uids
                print(f"\n📧 Checking last {len(recent_uids)} emails:")
                
                for uid in recent_uids:
                    uid_int = int(uid.decode())
                    typ, msg_data = imap.uid('fetch', uid, '(RFC822.HEADER)')
                    if typ == 'OK' and msg_data[0]:
                        email_message = email.message_from_bytes(msg_data[0][1])
                        subject = decode_header_value(email_message.get('Subject', ''))
                        sender = decode_header_value(email_message.get('From', ''))
                        date = email_message.get('Date', '')
                        
                        print(f"  UID {uid_int}: From: {sender}")
                        print(f"    Subject: {subject}")
                        print(f"    Date: {date}")
                        
                        # Check if this is from samhere@gmail.com
                        if 'samhere@gmail.com' in sender.lower():
                            print(f"  🎯 FOUND EMAIL FROM samhere@gmail.com!")
                        print()
            else:
                print("ℹ️  No new emails since last UID 784")
    
    # Close connection
    imap.close()
    imap.logout()
    print("✅ Connection closed successfully")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")