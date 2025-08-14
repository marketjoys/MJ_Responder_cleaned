#!/usr/bin/env python3
import imaplib
import ssl
import email
import re
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
    print(f"🔍 Checking SPAM folder for emails from samhere@gmail.com...")
    
    # Connect
    context = ssl.create_default_context()
    imap = imaplib.IMAP4_SSL(imap_server, imap_port, ssl_context=context)
    imap.login(email_account, password)
    
    # List all folders
    print("📁 Available folders:")
    typ, folders = imap.list()
    for folder in folders:
        folder_name = folder.decode().split('"')[3] if folder else ""
        if 'spam' in folder_name.lower() or 'junk' in folder_name.lower():
            print(f"   📧 Found spam folder: {folder_name}")
    
    # Check common spam folder names
    spam_folders = ['[Gmail]/Spam', 'INBOX.Junk', 'Junk', 'Spam']
    
    for spam_folder in spam_folders:
        try:
            print(f"\n🗂️  Checking folder: {spam_folder}")
            result = imap.select(spam_folder)
            if result[0] == 'OK':
                print(f"✅ Successfully selected {spam_folder}")
                
                # Search for emails from samhere@gmail.com
                typ, msg_ids = imap.search(None, 'FROM', 'samhere@gmail.com')
                if typ == 'OK' and msg_ids[0]:
                    email_ids = msg_ids[0].split()
                    print(f"🎯 FOUND {len(email_ids)} emails from samhere@gmail.com in {spam_folder}!")
                    
                    # Show details of the latest one
                    if email_ids:
                        latest_id = email_ids[-1]
                        typ, msg_data = imap.fetch(latest_id, '(RFC822.HEADER)')
                        if typ == 'OK' and msg_data[0]:
                            email_message = email.message_from_bytes(msg_data[0][1])
                            subject = decode_header_value(email_message.get('Subject', ''))
                            date = email_message.get('Date', '')
                            print(f"   📍 Subject: {subject}")
                            print(f"   📍 Date: {date}")
                else:
                    print(f"   📭 No emails from samhere@gmail.com in {spam_folder}")
            else:
                print(f"   ❌ Could not select {spam_folder}")
        except Exception as e:
            print(f"   ⚠️  Error checking {spam_folder}: {str(e)}")
    
    # Close connection
    imap.close()
    imap.logout()
    print("\n✅ Spam check completed")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")