import imaplib
import smtplib
import ssl
import email
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from email.utils import parseaddr, formataddr
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import re
import time
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from pydantic import BaseModel, Field
import json
import uuid
from email_reply_parser import EmailReplyParser

logger = logging.getLogger(__name__)

# EmailMessage will be imported from server to avoid duplication

class EmailConnection:
    """Handles IMAP and SMTP connections for an email account"""
    
    def __init__(self, account_config: Dict[str, Any]):
        self.account_config = account_config
        self.account_id = account_config['id']
        self.email = account_config['email']
        self.username = account_config['username']
        self.password = account_config['password']
        self.imap_server = account_config['imap_server']
        self.imap_port = account_config['imap_port']
        self.smtp_server = account_config['smtp_server']
        self.smtp_port = account_config['smtp_port']
        
        self.imap_connection = None
        self.last_uid = account_config.get('last_uid', 0)
        self.uidvalidity = account_config.get('uidvalidity', None)
        
    def _convert_signature_to_html(self, signature: str) -> str:
        """Convert signature to proper HTML format, handling both plain text and HTML signatures"""
        if not signature:
            return ""
        
        import html
        import re
        
        # Check if signature is already HTML (contains <br> or other HTML tags)
        is_html_signature = bool(re.search(r'<[^>]+>', signature))
        
        if is_html_signature:
            # Signature is already HTML, just enhance with links if needed
            html_signature = signature
            # Convert email addresses to mailto links (only if not already linked)
            email_pattern = r'\b(?<!href="mailto:)([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b'
            html_signature = re.sub(email_pattern, r'<a href="mailto:\1">\1</a>', html_signature)
            # Convert URLs to clickable links (only if not already linked)
            url_pattern = r'(?<!href=")(https?://[^\s<>"{}|\\^`\[\]]+)(?!")'
            html_signature = re.sub(url_pattern, r'<a href="\1" target="_blank">\1</a>', html_signature)
            return html_signature
        else:
            # Signature is plain text, process normally
            # Escape HTML characters first
            html_signature = html.escape(signature)
            
            # Convert newlines to <br> tags
            html_signature = html_signature.replace('\n', '<br>')
            
            # Convert email addresses to mailto links
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            html_signature = re.sub(email_pattern, r'<a href="mailto:\g<0>">\g<0></a>', html_signature)
            
            # Convert URLs to clickable links
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            html_signature = re.sub(url_pattern, r'<a href="\g<0>" target="_blank">\g<0></a>', html_signature)
            
            return html_signature

    def _is_connection_healthy(self) -> bool:
        """Check if IMAP connection is healthy and ready to use"""
        if not self.imap_connection:
            logger.debug(f"🔍 No IMAP connection exists for {self.email}")
            return False
        
        try:
            # Try to send a NOOP command to test the connection
            self.imap_connection.noop()
            logger.debug(f"✅ IMAP connection healthy for {self.email}")
            return True
        except Exception as e:
            logger.warning(f"⚠️  IMAP connection unhealthy for {self.email}: {str(e)}")
            return False
    
    def connect_imap(self) -> bool:
        """Connect to IMAP server"""
        try:
            # Create SSL context
            context = ssl.create_default_context()
            
            # Connect to IMAP server
            self.imap_connection = imaplib.IMAP4_SSL(self.imap_server, self.imap_port, ssl_context=context)
            
            # Login with error handling
            try:
                self.imap_connection.login(self.username, self.password)
            except imaplib.IMAP4.error as login_error:
                logger.error(f"❌ IMAP login failed for {self.email}: {str(login_error)}")
                self.imap_connection = None
                return False
            
            # Select INBOX
            status, messages = self.imap_connection.select('INBOX')
            if status != 'OK':
                logger.error(f"❌ Failed to select INBOX for {self.email}: {messages}")
                self.imap_connection = None
                return False
            
            logger.info(f"✅ IMAP connected for {self.email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ IMAP connection failed for {self.email}: {str(e)}")
            self.imap_connection = None
            return False
    
    def disconnect_imap(self):
        """Disconnect from IMAP server"""
        if self.imap_connection:
            try:
                self.imap_connection.close()
                self.imap_connection.logout()
            except:
                pass
            self.imap_connection = None
    
    def fetch_new_emails(self) -> List[Dict[str, Any]]:
        """Fetch new emails from IMAP server"""
        # Check if connection exists and is healthy
        if not self._is_connection_healthy():
            if not self.connect_imap():
                logger.error(f"❌ Failed to establish IMAP connection for {self.email}")
                return []
        
        try:
            # Test connection health by sending a NOOP command
            try:
                self.imap_connection.noop()  # Keep alive and test connection
                logger.debug(f"🔄 Connection confirmed healthy for {self.email}")
            except Exception as noop_error:
                logger.warning(f"⚠️  Connection health check failed for {self.email}: {noop_error}")
                # Try to reconnect
                self.disconnect_imap()
                if not self.connect_imap():
                    return []
            
            # Check UIDVALIDITY for this mailbox
            try:
                response = self.imap_connection.response('UIDVALIDITY')
                if response and response[1] and response[1][0]:
                    current_uidvalidity = response[1][0].decode() if isinstance(response[1][0], bytes) else str(response[1][0])
                    if self.uidvalidity and self.uidvalidity != current_uidvalidity:
                        # UIDVALIDITY changed, reset last_uid
                        logger.warning(f"UIDVALIDITY changed for {self.email}, resetting UID tracking")
                        self.last_uid = 0
                    self.uidvalidity = current_uidvalidity
            except Exception as uidvalidity_error:
                logger.warning(f"⚠️  Could not parse UIDVALIDITY for {self.email}: {uidvalidity_error}")
                pass  # Continue without UIDVALIDITY checking
            
            # Search for messages newer than last processed UID
            if self.last_uid > 0:
                # Search for UIDs greater than last processed
                typ, msg_ids = self.imap_connection.uid('search', None, f'UID {self.last_uid+1}:*')
            else:
                # First time polling - get the latest UID to start from (don't process existing emails)
                typ, all_msg_ids = self.imap_connection.uid('search', None, 'ALL')
                if typ == 'OK' and all_msg_ids[0]:
                    try:
                        all_uids = [uid for uid in all_msg_ids[0].split() if uid]
                        if all_uids:
                            # Set last_uid to the latest existing email so we only process future emails
                            self.last_uid = int(all_uids[-1].decode())
                            logger.info(f"🔄 First-time polling setup for {self.email}. Starting from UID {self.last_uid}")
                    except (ValueError, UnicodeDecodeError, IndexError) as setup_error:
                        logger.warning(f"⚠️  Could not setup UID tracking for {self.email}: {setup_error}")
                        self.last_uid = 0
                return []  # Don't process any existing emails on first run
            
            if typ != 'OK' or not msg_ids[0]:
                return []
            
            # Split and filter out empty UIDs
            uids = [uid for uid in msg_ids[0].split() if uid]
            new_emails = []
            
            for uid in uids:
                try:
                    uid_int = int(uid.decode())
                    if uid_int <= self.last_uid:
                        continue
                        
                    email_data = self._fetch_email_by_uid(uid)
                    if email_data:
                        new_emails.append(email_data)
                        self.last_uid = max(self.last_uid, uid_int)
                except (ValueError, UnicodeDecodeError) as decode_error:
                    logger.warning(f"⚠️  Skipping invalid UID for {self.email}: {uid} - {decode_error}")
                    continue
            
            logger.info(f"📧 Fetched {len(new_emails)} new emails for {self.email}")
            return new_emails
            
        except Exception as e:
            logger.error(f"❌ Error fetching emails for {self.email}: {str(e)}")
            self.disconnect_imap()
            return []
    
    def _fetch_email_by_uid(self, uid) -> Optional[Dict[str, Any]]:
        """Fetch a single email by UID"""
        try:
            # Fetch email data
            typ, msg_data = self.imap_connection.uid('fetch', uid, '(RFC822)')
            if typ != 'OK' or not msg_data[0]:
                return None
            
            # Parse email
            email_message = email.message_from_bytes(msg_data[0][1])
            
            # Extract email details
            subject = self._decode_header(email_message.get('Subject', ''))
            sender = self._decode_header(email_message.get('From', ''))
            recipient = self._decode_header(email_message.get('To', ''))
            date_str = email_message.get('Date', '')
            message_id = email_message.get('Message-ID', '')
            in_reply_to = email_message.get('In-Reply-To', '')
            references = email_message.get('References', '')
            
            # Parse date
            try:
                received_at = email.utils.parsedate_to_datetime(date_str)
            except:
                received_at = datetime.utcnow()
            
            # Extract body
            body, body_html = self._extract_body(email_message)
            
            # Clean body using email reply parser
            if body:
                body = EmailReplyParser.parse_reply(body)
            
            # Generate thread ID
            thread_id = self._generate_thread_id(message_id, in_reply_to, references, subject)
            
            return {
                'uid': int(uid.decode()),
                'message_id': message_id,
                'thread_id': thread_id,
                'subject': subject,
                'sender': sender,
                'recipient': recipient,
                'body': body or '',
                'body_html': body_html or '',
                'received_at': received_at,
                'in_reply_to': in_reply_to,
                'references': references,
                'account_id': self.account_id
            }
            
        except Exception as e:
            logger.error(f"❌ Error parsing email UID {uid}: {str(e)}")
            return None
    
    def _decode_header(self, header_value: str) -> str:
        """Decode email header value"""
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
    
    def _extract_body(self, email_message) -> Tuple[Optional[str], Optional[str]]:
        """Extract plain text and HTML body from email"""
        body = None
        body_html = None
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                
                if content_type == "text/plain" and not body:
                    try:
                        charset = part.get_content_charset() or 'utf-8'
                        body = part.get_payload(decode=True).decode(charset, errors='ignore')
                    except:
                        pass
                elif content_type == "text/html" and not body_html:
                    try:
                        charset = part.get_content_charset() or 'utf-8'
                        body_html = part.get_payload(decode=True).decode(charset, errors='ignore')
                    except:
                        pass
        else:
            # Single part message
            content_type = email_message.get_content_type()
            try:
                charset = email_message.get_content_charset() or 'utf-8'
                content = email_message.get_payload(decode=True).decode(charset, errors='ignore')
                
                if content_type == "text/html":
                    body_html = content
                else:
                    body = content
            except:
                pass
        
        return body, body_html
    
    def _generate_thread_id(self, message_id: str, in_reply_to: str, references: str, subject: str) -> str:
        """Generate thread ID for email conversation tracking"""
        # If this is a reply, use the original message ID from In-Reply-To or References
        if in_reply_to:
            return in_reply_to.strip('<>')
        
        if references:
            # Get the first message ID from references
            ref_ids = references.split()
            if ref_ids:
                return ref_ids[0].strip('<>')
        
        # Clean subject for thread matching
        clean_subject = re.sub(r'^(re:|fwd?:)\s*', '', subject.lower().strip())
        thread_hash = str(hash(f"{clean_subject}_{self.email}"))
        
        return f"thread-{thread_hash}"
    
    def mark_email_as_read(self, uid: int) -> bool:
        """Mark email as read by UID"""
        try:
            if not self.imap_connection:
                if not self.connect_imap():
                    return False
            
            # Mark as seen (read)
            self.imap_connection.uid('store', str(uid), '+FLAGS', '(\\Seen)')
            logger.info(f"📖 Marked email UID {uid} as read for {self.email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error marking email UID {uid} as read for {self.email}: {str(e)}")
            return False
    
    def send_email(self, to_email: str, subject: str, body: str, body_html: str = None, 
                   in_reply_to: str = None, references: str = None, 
                   message_id_to_reply: str = None, signature_already_included: bool = False) -> bool:
        """Send email via SMTP
        
        Args:
            signature_already_included: If True, skip adding signature (prevents double signatures)
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = formataddr((self.account_config.get('name', ''), self.email))
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Set threading headers
            if in_reply_to:
                msg['In-Reply-To'] = in_reply_to
            elif message_id_to_reply:
                msg['In-Reply-To'] = message_id_to_reply
            
            if references:
                msg['References'] = references
            elif message_id_to_reply:
                msg['References'] = message_id_to_reply
            
            # Generate unique Message-ID
            msg['Message-ID'] = f"<{uuid.uuid4()}@{self.email.split('@')[1]}>"
            
            # Add signature if configured AND not already included
            signature = self.account_config.get('signature', '')
            if signature and not signature_already_included:
                if body:
                    # Check if signature is HTML and convert to plain text for plain text email
                    import re
                    import html
                    is_html_signature = bool(re.search(r'<[^>]+>', signature))
                    if is_html_signature:
                        # Convert HTML signature to plain text
                        plain_signature = re.sub(r'<br\s*/?>', '\n', signature, flags=re.IGNORECASE)
                        plain_signature = re.sub(r'<[^>]+>', '', plain_signature)  # Remove all HTML tags
                        plain_signature = html.unescape(plain_signature)  # Unescape HTML entities
                        body += f"\n\n{plain_signature.strip()}"
                    else:
                        body += f"\n\n{signature}"
                if body_html:
                    # Properly convert signature to HTML
                    html_signature = self._convert_signature_to_html(signature)
                    body_html += f"<br><br>{html_signature}"
            
            # Add body parts with signature included
            if body:
                text_part = MIMEText(body, 'plain', 'utf-8')
                msg.attach(text_part)
            
            if body_html:
                html_part = MIMEText(body_html, 'html', 'utf-8')
                msg.attach(html_part)
            
            # Connect to SMTP and send
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"✅ Email sent from {self.email} to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send email from {self.email}: {str(e)}")
            return False


class EmailPollingService:
    """Service to poll email accounts and process new messages"""
    
    def __init__(self, mongo_url: str, db_name: str):
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client[db_name]
        self.is_running = False
        self.connections = {}
        
    async def start_polling(self):
        """Start the email polling service"""
        self.is_running = True
        logger.info("🚀 Starting email polling service...")
        
        poll_count = 0
        while self.is_running:
            try:
                poll_count += 1
                logger.info(f"🔄 Starting poll cycle #{poll_count}")
                
                await self._poll_all_accounts()
                
                logger.info(f"✅ Poll cycle #{poll_count} completed. Active connections: {len(self.connections)}")
                await asyncio.sleep(60)  # Poll every 60 seconds
                
            except Exception as e:
                logger.error(f"❌ Error in polling loop (cycle #{poll_count}): {str(e)}")
                # Continue running even if one cycle fails
                await asyncio.sleep(60)
    
    def stop_polling(self):
        """Stop the email polling service"""
        self.is_running = False
        for connection in self.connections.values():
            connection.disconnect_imap()
        self.connections.clear()
        logger.info("🛑 Email polling service stopped")
    
    async def _poll_all_accounts(self):
        """Poll all active email accounts"""
        try:
            # Get all active email accounts
            accounts = await self.db.email_accounts.find({"is_active": True}).to_list(100)
            
            for account in accounts:
                await self._poll_account(account)
                
        except Exception as e:
            logger.error(f"❌ Error polling accounts: {str(e)}")
    
    async def _poll_account(self, account: Dict[str, Any]):
        """Poll a single email account"""
        account_id = account['id']
        
        try:
            # Check if this is an OAuth account
            if account.get('use_oauth', False) and account.get('auth_type') == 'oauth':
                # Handle OAuth account differently
                await self._poll_oauth_account(account)
                return
            
            # Handle traditional IMAP account
            # Get or create connection
            if account_id not in self.connections:
                logger.info(f"🔌 Creating new connection for {account.get('email', account_id)}")
                self.connections[account_id] = EmailConnection(account)
            else:
                logger.debug(f"🔄 Reusing existing connection for {account.get('email', account_id)}")
            
            connection = self.connections[account_id]
            
            # Update connection with latest account data from database
            # This ensures we have the most recent last_uid and uidvalidity
            latest_account = await self.db.email_accounts.find_one({"id": account_id})
            if latest_account:
                connection.last_uid = latest_account.get('last_uid', 0)
                connection.uidvalidity = latest_account.get('uidvalidity', None)
                logger.debug(f"🔄 Updated connection last_uid to {connection.last_uid} for {connection.email}")
            
            # Fetch new emails - connection will be validated/recreated if needed
            new_emails = connection.fetch_new_emails()
            
            # Always update last UID and last_polled in database (even if no new emails)
            await self.db.email_accounts.update_one(
                {"id": account_id},
                {"$set": {
                    "last_uid": connection.last_uid,
                    "uidvalidity": connection.uidvalidity,
                    "last_polled": datetime.utcnow()
                }}
            )
            
            if new_emails:
                logger.info(f"📥 Processing {len(new_emails)} new emails for {connection.email}")
                # Process each new email
                for email_data in new_emails:
                    await self._process_new_email(email_data)
            else:
                logger.debug(f"📭 No new emails for {connection.email}")
                
        except Exception as e:
            logger.error(f"❌ Error polling account {account.get('email', account_id)}: {str(e)}")
            # Remove connection on error to force reconnect on next poll
            if account_id in self.connections:
                try:
                    self.connections[account_id].disconnect_imap()
                except Exception as disconnect_error:
                    logger.warning(f"⚠️  Error disconnecting IMAP for {account.get('email', account_id)}: {disconnect_error}")
                del self.connections[account_id]
                logger.info(f"🔌 Removed unhealthy connection for {account.get('email', account_id)}")
    
    async def _poll_oauth_account(self, account: Dict[str, Any]):
        """Poll OAuth-enabled email account using appropriate API (Google or Microsoft)"""
        account_id = account['id']
        oauth_email = account.get('oauth_email')
        provider_type = account.get('provider', '').lower()
        
        if not oauth_email:
            logger.error(f"❌ OAuth account {account_id} missing oauth_email field")
            return
        
        # Enhanced debugging for provider routing
        logger.info(f"🔍 OAUTH ROUTING DEBUG - Account ID: {account_id}")
        logger.info(f"🔍 OAuth Email: {oauth_email}")
        logger.info(f"🔍 Provider (from account): {account.get('provider')}")
        logger.info(f"🔍 Auth Type: {account.get('auth_type')}")
        logger.info(f"🔍 Use OAuth: {account.get('use_oauth')}")
        
        # Determine provider type from account field first, then email domain
        if provider_type:
            logger.info(f"🔍 Using provider from account field: {provider_type}")
        else:
            email_domain = oauth_email.split('@')[-1].lower()
            logger.info(f"🔍 Email domain: {email_domain}")
            
            if 'gmail.com' in email_domain or 'googlemail.com' in email_domain:
                provider_type = 'google'
                logger.info(f"🔍 Domain-based provider detection: {provider_type}")
            elif ('outlook.com' in email_domain or 'hotmail.com' in email_domain or 
                  'live.com' in email_domain or 'office365.com' in email_domain or 
                  'onmicrosoft.com' in email_domain):
                provider_type = 'microsoft'
                logger.info(f"🔍 Domain-based provider detection: {provider_type}")
            else:
                logger.warning(f"⚠️ Unknown OAuth provider for {oauth_email} (domain: {email_domain}), defaulting to Google")
                provider_type = 'google'
        
        # Normalize provider type - handle both "outlook" and "microsoft"
        original_provider = provider_type
        if provider_type.lower() in ['outlook', 'microsoft']:
            provider_type = 'microsoft'
        elif provider_type.lower() in ['gmail', 'google']:
            provider_type = 'google'
        
        if original_provider != provider_type:
            logger.info(f"🔄 Normalized provider: {original_provider} -> {provider_type}")
        
        logger.info(f"🚀 FINAL ROUTING: Polling OAuth account {oauth_email} using {provider_type.upper()} API")
        
        try:
            if provider_type == 'microsoft':
                await self._poll_microsoft_oauth_account(account, oauth_email)
            else:
                await self._poll_google_oauth_account(account, oauth_email)
                
        except Exception as e:
            logger.error(f"❌ Error polling OAuth account {oauth_email} (provider: {provider_type}): {str(e)}")
            # Re-raise to allow upper levels to handle
            raise

    async def _poll_google_oauth_account(self, account: Dict[str, Any], oauth_email: str):
        """Poll Google OAuth account using Gmail API"""
        account_id = account['id']
        
        try:
            # Import here to avoid circular imports
            from google_services import get_google_gmail_service
            
            # Get Gmail service for this specific OAuth account
            gmail_service = await get_google_gmail_service(account['user_id'], oauth_email)
            
            # Get last processed message timestamp from database
            last_processed = account.get('last_oauth_sync', None)
            
            # Ensure last_processed is timezone-naive for comparison
            if last_processed and hasattr(last_processed, 'tzinfo') and last_processed.tzinfo is not None:
                last_processed = last_processed.replace(tzinfo=None)
            
            # Build query for new messages
            query = "in:inbox"
            if last_processed:
                # Format datetime for Gmail API query
                after_date = last_processed.strftime('%Y/%m/%d')
                query += f" after:{after_date}"
            
            # List new messages
            messages = await gmail_service.list_messages(query=query, max_results=50)
            
            new_emails = []
            latest_processed = last_processed or datetime.utcnow()
            
            for message_info in messages:
                try:
                    # Get full message
                    full_message = await gmail_service.get_message(message_info['id'])
                    
                    # Parse Gmail API message
                    email_data = await self._parse_gmail_message(full_message, account_id)
                    comparison_time = last_processed if last_processed else datetime.min
                    if email_data and email_data['received_at'] > comparison_time:
                        new_emails.append(email_data)
                        latest_processed = max(latest_processed, email_data['received_at'])
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error processing Gmail message {message_info['id']}: {str(e)}")
                    continue
            
            # Update last sync time
            await self.db.email_accounts.update_one(
                {"id": account_id},
                {"$set": {
                    "last_oauth_sync": latest_processed,
                    "last_polled": datetime.utcnow()
                }}
            )
            
            if new_emails:
                logger.info(f"📥 Processing {len(new_emails)} new Google OAuth emails for {oauth_email}")
                # Process each new email
                for email_data in new_emails:
                    await self._process_new_email(email_data)
            else:
                logger.debug(f"📭 No new Google OAuth emails for {oauth_email}")
                
        except Exception as e:
            logger.error(f"❌ Error polling Google OAuth account {oauth_email}: {str(e)}")
            raise

    async def _poll_microsoft_oauth_account(self, account: Dict[str, Any], oauth_email: str):
        """Poll Microsoft OAuth account using Microsoft Graph API"""
        account_id = account['id']
        
        try:
            # Import here to avoid circular imports
            from microsoft_services import MicrosoftMailService
            
            # Get Microsoft Mail service for this user with specific OAuth email
            mail_service = MicrosoftMailService(account['user_id'], oauth_email)
            
            # Get last processed message timestamp from database
            last_processed = account.get('last_oauth_sync', None)
            
            # Ensure last_processed is timezone-naive for comparison
            if last_processed and hasattr(last_processed, 'tzinfo') and last_processed.tzinfo is not None:
                last_processed = last_processed.replace(tzinfo=None)
            
            # Get messages from inbox (Microsoft Graph API automatically returns newest first)
            messages = await mail_service.list_messages(folder='inbox', max_results=50)
            
            new_emails = []
            latest_processed = last_processed or datetime.utcnow()
            
            for message in messages:
                try:
                    # Parse Microsoft Graph message received time
                    received_time_str = message.get('receivedDateTime', '')
                    if received_time_str:
                        # Parse ISO format datetime
                        received_at = datetime.fromisoformat(received_time_str.replace('Z', '+00:00'))
                        received_at = received_at.replace(tzinfo=None)  # Remove timezone for comparison
                        
                        # Only process messages newer than last processed
                        comparison_time = last_processed if last_processed else datetime.min
                        if received_at > comparison_time:
                            # Get full message details
                            full_message = await mail_service.get_message(message['id'])
                            
                            # Parse Microsoft Graph message
                            email_data = await self._parse_microsoft_message(full_message, account_id)
                            if email_data:
                                new_emails.append(email_data)
                                latest_processed = max(latest_processed, received_at)
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error processing Microsoft message {message.get('id', 'unknown')}: {str(e)}")
                    continue
            
            # Update last sync time
            await self.db.email_accounts.update_one(
                {"id": account_id},
                {"$set": {
                    "last_oauth_sync": latest_processed,
                    "last_polled": datetime.utcnow()
                }}
            )
            
            if new_emails:
                logger.info(f"📥 Processing {len(new_emails)} new Microsoft OAuth emails for {oauth_email}")
                # Process each new email
                for email_data in new_emails:
                    await self._process_new_email(email_data)
            else:
                logger.debug(f"📭 No new Microsoft OAuth emails for {oauth_email}")
                
        except Exception as e:
            logger.error(f"❌ Error polling Microsoft OAuth account {oauth_email}: {str(e)}")
            raise
    
    async def _parse_gmail_message(self, gmail_message: Dict[str, Any], account_id: str) -> Optional[Dict[str, Any]]:
        """Parse Gmail API message to our email format"""
        try:
            import base64
            
            # Decode raw message
            raw_data = gmail_message.get('raw', '')
            if not raw_data:
                return None
            
            # Decode base64 message
            message_bytes = base64.urlsafe_b64decode(raw_data + '==')  # Add padding
            email_message = email.message_from_bytes(message_bytes)
            
            # Extract basic fields
            subject = email_message.get('Subject', '')
            sender = email_message.get('From', '')
            recipient = email_message.get('To', '')
            date_str = email_message.get('Date', '')
            message_id = email_message.get('Message-ID', '')
            in_reply_to = email_message.get('In-Reply-To', '')
            references = email_message.get('References', '')
            
            # Parse date
            try:
                received_at = email.utils.parsedate_to_datetime(date_str)
            except:
                received_at = datetime.utcnow()
            
            # Extract body using existing method
            connection = EmailConnection({'id': account_id, 'email': recipient})  # Dummy connection for method
            body, body_html = connection._extract_body(email_message)
            
            # Clean body using email reply parser
            if body:
                body = EmailReplyParser.parse_reply(body)
            
            # Generate thread ID
            thread_id = connection._generate_thread_id(message_id, in_reply_to, references, subject)
            
            return {
                'gmail_id': gmail_message.get('id'),
                'message_id': message_id,
                'thread_id': thread_id,
                'subject': subject,
                'sender': sender,
                'recipient': recipient,
                'body': body or '',
                'body_html': body_html or '',
                'received_at': received_at,
                'in_reply_to': in_reply_to,
                'references': references,
                'account_id': account_id
            }
            
        except Exception as e:
            logger.error(f"❌ Error parsing Gmail message: {str(e)}")
            return None

    async def _parse_microsoft_message(self, microsoft_message: Dict[str, Any], account_id: str) -> Optional[Dict[str, Any]]:
        """Parse Microsoft Graph API message to our email format"""
        try:
            # Extract basic fields from Microsoft Graph API response
            subject = microsoft_message.get('subject', '')
            
            # Extract sender information
            sender_info = microsoft_message.get('from', {}).get('emailAddress', {})
            sender = f"{sender_info.get('name', '')} <{sender_info.get('address', '')}>"
            
            # Extract recipient information
            to_recipients = microsoft_message.get('toRecipients', [])
            recipients = []
            for recipient in to_recipients:
                email_addr = recipient.get('emailAddress', {})
                recipients.append(f"{email_addr.get('name', '')} <{email_addr.get('address', '')}>")
            recipient = ', '.join(recipients) if recipients else ''
            
            # Parse received date
            received_time_str = microsoft_message.get('receivedDateTime', '')
            try:
                if received_time_str:
                    received_at = datetime.fromisoformat(received_time_str.replace('Z', '+00:00'))
                    received_at = received_at.replace(tzinfo=None)  # Remove timezone
                else:
                    received_at = datetime.utcnow()
            except:
                received_at = datetime.utcnow()
            
            # Extract message ID and conversation ID
            message_id = microsoft_message.get('internetMessageId', '') or f"ms-{microsoft_message.get('id', '')}"
            conversation_id = microsoft_message.get('conversationId', '')
            
            # Extract body content
            body_content = microsoft_message.get('body', {})
            body_html = body_content.get('content', '') if body_content.get('contentType') == 'html' else ''
            
            # Convert HTML to plain text for body field
            body = ''
            if body_html:
                import re
                # Simple HTML to text conversion
                body = re.sub(r'<[^>]+>', '', body_html)
                body = re.sub(r'\s+', ' ', body).strip()
            
            if not body:
                body = microsoft_message.get('bodyPreview', '')
            
            # Clean body using email reply parser
            if body:
                try:
                    from email_reply_parser import EmailReplyParser
                    body = EmailReplyParser.parse_reply(body)
                except:
                    pass  # If email-reply-parser fails, use original body
            
            # Generate thread ID using conversation ID or message ID
            thread_id = conversation_id or f"ms-thread-{message_id}"
            
            # Extract In-Reply-To and References from internet message headers if available
            internet_headers = microsoft_message.get('internetMessageHeaders', [])
            in_reply_to = ''
            references = ''
            
            for header in internet_headers:
                header_name = header.get('name', '').lower()
                header_value = header.get('value', '')
                if header_name == 'in-reply-to':
                    in_reply_to = header_value
                elif header_name == 'references':
                    references = header_value
            
            return {
                'microsoft_id': microsoft_message.get('id'),
                'message_id': message_id,
                'thread_id': thread_id,
                'subject': subject,
                'sender': sender,
                'recipient': recipient,
                'body': body or '',
                'body_html': body_html or '',
                'received_at': received_at,
                'in_reply_to': in_reply_to,
                'references': references,
                'account_id': account_id,
                'conversation_id': conversation_id
            }
            
        except Exception as e:
            logger.error(f"❌ Error parsing Microsoft message: {str(e)}")
            return None
    
    async def _process_new_email(self, email_data: Dict[str, Any]):
        """Process a new email through the AI workflow"""
        try:
            # Check for duplicates
            existing = await self.db.emails.find_one({
                "message_id": email_data['message_id'],
                "account_id": email_data['account_id']
            })
            
            if existing:
                return  # Skip duplicate
            
            # Get user_id from the account
            account_doc = await self.db.email_accounts.find_one({"id": email_data['account_id']})
            if not account_doc:
                logger.error(f"Account {email_data['account_id']} not found for email processing")
                return
            
            user_id = account_doc.get("user_id")
            if not user_id:
                logger.error(f"No user_id found for account {email_data['account_id']}")
                return
            
            # Import EmailMessage dynamically to avoid circular imports
            from server import EmailMessage
            
            # Create email record
            email_obj = EmailMessage(
                account_id=email_data['account_id'],
                user_id=user_id,  # Set user_id from account
                message_id=email_data['message_id'],
                thread_id=email_data['thread_id'],
                subject=email_data['subject'],
                sender=email_data['sender'],
                recipient=email_data['recipient'],
                body=email_data['body'],
                body_html=email_data['body_html'],
                received_at=email_data['received_at'],
                status="new"
            )
            
            # Store in database
            await self.db.emails.insert_one(email_obj.dict())
            
            # Mark email as read to prevent reprocessing
            if 'uid' in email_data:
                # Get the connection to mark as read
                account_doc = await self.db.email_accounts.find_one({"id": email_data['account_id']})
                if account_doc and account_doc['id'] in self.connections:
                    connection = self.connections[account_doc['id']]
                    connection.mark_email_as_read(email_data['uid'])
            
            # Process through AI workflow (async) using RQ if available
            try:
                # Try to use RQ message broker
                from tasks import enqueue_email_processing, RQ_ENABLED
                if RQ_ENABLED:
                    job = enqueue_email_processing(email_obj.id)
                    logger.info(f"📋 Enqueued email processing via RQ: {email_obj.id}")
                else:
                    # Fallback to direct async processing
                    asyncio.create_task(self._process_email_ai_workflow(email_obj.id))
            except ImportError:
                # RQ not available, use direct async processing
                asyncio.create_task(self._process_email_ai_workflow(email_obj.id))
            
            logger.info(f"📥 New email processed: {email_data['subject']} from {email_data['sender']}")
            
        except Exception as e:
            logger.error(f"❌ Error processing new email: {str(e)}")
    
    async def _process_email_ai_workflow(self, email_id: str):
        """Process email through AI workflow - delegate to server's process_email_async"""
        try:
            # Import the function dynamically to avoid circular imports
            import importlib
            server_module = importlib.import_module('server')
            process_func = getattr(server_module, 'process_email_async')
            
            # Delegate to server's complete AI workflow
            await process_func(email_id)
                
        except Exception as e:
            logger.error(f"❌ Error in AI workflow for email {email_id}: {str(e)}")
            # Update email with error status
            await self.db.emails.update_one(
                {"id": email_id},
                {"$set": {"status": "error", "error": str(e)}}
            )
    
    async def _auto_send_email(self, email_id: str):
        """Automatically send approved email"""
        try:
            # Get email
            email_doc = await self.db.emails.find_one({"id": email_id})
            if not email_doc or email_doc['status'] != 'ready_to_send':
                return
            
            # Get account
            account_doc = await self.db.email_accounts.find_one({"id": email_doc['account_id']})
            if not account_doc or not account_doc.get('is_active') or not account_doc.get('auto_send', True):
                return
            
            # Create connection
            connection = EmailConnection(account_doc)
            
            # Extract sender email
            sender_email = email_doc['sender']
            if '<' in sender_email:
                sender_email = sender_email.split('<')[1].split('>')[0]
            
            # Prepare reply subject
            subject = email_doc['subject']
            if not subject.lower().startswith('re:'):
                subject = f"Re: {subject}"
            
            # Send email
            success = connection.send_email(
                to_email=sender_email,
                subject=subject,
                body=email_doc['draft'],
                body_html=email_doc['draft_html'],
                message_id_to_reply=email_doc['message_id'],
                references=email_doc.get('references', '')
            )
            
            if success:
                # Update status to sent
                await self.db.emails.update_one(
                    {"id": email_id},
                    {"$set": {
                        "status": "sent",
                        "sent_at": datetime.utcnow()
                    }}
                )
                logger.info(f"✅ Auto-sent reply for email: {email_doc['subject']}")
            else:
                # Mark as failed to send
                await self.db.emails.update_one(
                    {"id": email_id},
                    {"$set": {"status": "send_failed"}}
                )
                
        except Exception as e:
            logger.error(f"❌ Error auto-sending email {email_id}: {str(e)}")
            await self.db.emails.update_one(
                {"id": email_id},
                {"$set": {"status": "send_failed", "error": str(e)}}
            )

# Global polling service instance
polling_service = None

def get_polling_service(mongo_url: str, db_name: str) -> EmailPollingService:
    """Get or create the global polling service instance"""
    global polling_service
    if polling_service is None:
        polling_service = EmailPollingService(mongo_url, db_name)
    return polling_service
