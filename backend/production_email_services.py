"""
Production-ready Email Services with Enhanced Connection Pooling
Redesigned for handling 50k+ emails with intelligent connection management
"""
import imaplib
import smtplib
import ssl
import email
import logging
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from email.utils import parseaddr, formataddr
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import re
import time
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json
import uuid
from email_reply_parser import EmailReplyParser
from concurrent.futures import ThreadPoolExecutor
import threading
from queue import Queue, Empty
from dataclasses import dataclass
import hashlib

from config import config
from redis_manager import queue_manager, QueueNames, QueueTask
from enhanced_email_processor import enhanced_email_processor

logger = logging.getLogger(__name__)

@dataclass
class ConnectionPoolConfig:
    """Configuration for connection pools"""
    max_connections: int
    min_connections: int
    connection_timeout: int
    max_idle_time: int
    health_check_interval: int

class ProductionConnectionPool:
    """Production-ready connection pool for IMAP/SMTP"""
    
    def __init__(self, account_config: Dict[str, Any], pool_config: ConnectionPoolConfig):
        self.account_config = account_config
        self.pool_config = pool_config
        self.account_id = account_config['id']
        self.email = account_config['email']
        
        # Connection pools
        self.imap_pool: Queue = Queue(maxsize=pool_config.max_connections)
        self.smtp_pool: Queue = Queue(maxsize=pool_config.max_connections)
        
        # Pool statistics
        self.imap_created = 0
        self.imap_active = 0
        self.smtp_created = 0
        self.smtp_active = 0
        
        # Thread safety
        self.lock = threading.Lock()
        self.initialized = False
        
    async def initialize(self):
        """Initialize connection pools"""
        try:
            # Create minimum number of connections
            await self._create_initial_connections()
            
            # Start pool maintenance task
            asyncio.create_task(self._pool_maintenance_task())
            
            self.initialized = True
            logger.info(f"✅ Connection pool initialized for {self.email}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize connection pool for {self.email}: {e}")
            raise
    
    async def _create_initial_connections(self):
        """Create initial pool of connections"""
        # Create IMAP connections
        for _ in range(self.pool_config.min_connections):
            try:
                connection = await self._create_imap_connection()
                if connection:
                    self.imap_pool.put((connection, time.time()))
                    self.imap_created += 1
            except Exception as e:
                logger.warning(f"⚠️ Failed to create initial IMAP connection: {e}")
        
        # Create SMTP connections (fewer needed)
        smtp_min = max(1, self.pool_config.min_connections // 2)
        for _ in range(smtp_min):
            try:
                connection = await self._create_smtp_connection()
                if connection:
                    self.smtp_pool.put((connection, time.time()))
                    self.smtp_created += 1
            except Exception as e:
                logger.warning(f"⚠️ Failed to create initial SMTP connection: {e}")
    
    async def _create_imap_connection(self) -> Optional[imaplib.IMAP4_SSL]:
        """Create a new IMAP connection"""
        try:
            context = ssl.create_default_context()
            connection = imaplib.IMAP4_SSL(
                self.account_config['imap_server'], 
                self.account_config['imap_port'], 
                ssl_context=context
            )
            
            # Login
            connection.login(
                self.account_config['username'], 
                self.account_config['password']
            )
            
            # Select INBOX
            status, messages = connection.select('INBOX')
            if status != 'OK':
                connection.logout()
                return None
            
            return connection
            
        except Exception as e:
            logger.error(f"❌ Failed to create IMAP connection for {self.email}: {e}")
            return None
    
    async def _create_smtp_connection(self) -> Optional[smtplib.SMTP]:
        """Create a new SMTP connection"""
        try:
            connection = smtplib.SMTP(
                self.account_config['smtp_server'], 
                self.account_config['smtp_port']
            )
            
            connection.starttls()
            connection.login(
                self.account_config['username'], 
                self.account_config['password']
            )
            
            return connection
            
        except Exception as e:
            logger.error(f"❌ Failed to create SMTP connection for {self.email}: {e}")
            return None
    
    async def get_imap_connection(self) -> Optional[imaplib.IMAP4_SSL]:
        """Get an IMAP connection from the pool"""
        try:
            # Try to get from pool
            try:
                connection, created_time = self.imap_pool.get_nowait()
                
                # Check if connection is still valid
                if time.time() - created_time < self.pool_config.max_idle_time:
                    if await self._test_imap_connection(connection):
                        with self.lock:
                            self.imap_active += 1
                        return connection
                    else:
                        # Connection is dead, close it
                        try:
                            connection.logout()
                        except:
                            pass
                
            except Empty:
                pass
            
            # Create new connection if pool is empty or connections are stale
            connection = await self._create_imap_connection()
            if connection:
                with self.lock:
                    self.imap_created += 1
                    self.imap_active += 1
                return connection
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get IMAP connection: {e}")
            return None
    
    async def get_smtp_connection(self) -> Optional[smtplib.SMTP]:
        """Get an SMTP connection from the pool"""
        try:
            # Try to get from pool
            try:
                connection, created_time = self.smtp_pool.get_nowait()
                
                # Check if connection is still valid
                if time.time() - created_time < self.pool_config.max_idle_time:
                    if await self._test_smtp_connection(connection):
                        with self.lock:
                            self.smtp_active += 1
                        return connection
                    else:
                        # Connection is dead, close it
                        try:
                            connection.quit()
                        except:
                            pass
                
            except Empty:
                pass
            
            # Create new connection
            connection = await self._create_smtp_connection()
            if connection:
                with self.lock:
                    self.smtp_created += 1
                    self.smtp_active += 1
                return connection
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get SMTP connection: {e}")
            return None
    
    async def _test_imap_connection(self, connection: imaplib.IMAP4_SSL) -> bool:
        """Test if IMAP connection is still alive"""
        try:
            connection.noop()
            return True
        except:
            return False
    
    async def _test_smtp_connection(self, connection: smtplib.SMTP) -> bool:
        """Test if SMTP connection is still alive"""
        try:
            connection.noop()
            return True
        except:
            return False
    
    def return_imap_connection(self, connection: imaplib.IMAP4_SSL):
        """Return IMAP connection to pool"""
        try:
            if connection and self.imap_pool.qsize() < self.pool_config.max_connections:
                self.imap_pool.put((connection, time.time()))
            else:
                # Pool is full, close connection
                try:
                    connection.logout()
                except:
                    pass
            
            with self.lock:
                self.imap_active = max(0, self.imap_active - 1)
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to return IMAP connection: {e}")
    
    def return_smtp_connection(self, connection: smtplib.SMTP):
        """Return SMTP connection to pool"""
        try:
            if connection and self.smtp_pool.qsize() < self.pool_config.max_connections:
                self.smtp_pool.put((connection, time.time()))
            else:
                # Pool is full, close connection
                try:
                    connection.quit()
                except:
                    pass
            
            with self.lock:
                self.smtp_active = max(0, self.smtp_active - 1)
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to return SMTP connection: {e}")
    
    async def _pool_maintenance_task(self):
        """Background task to maintain connection pools"""
        while True:
            try:
                await asyncio.sleep(self.pool_config.health_check_interval)
                
                # Clean up stale IMAP connections
                current_time = time.time()
                imap_to_remove = []
                
                temp_imap_connections = []
                while not self.imap_pool.empty():
                    try:
                        connection, created_time = self.imap_pool.get_nowait()
                        if current_time - created_time > self.pool_config.max_idle_time:
                            imap_to_remove.append(connection)
                        else:
                            temp_imap_connections.append((connection, created_time))
                    except Empty:
                        break
                
                # Return valid connections to pool
                for conn_tuple in temp_imap_connections:
                    self.imap_pool.put(conn_tuple)
                
                # Close stale connections
                for connection in imap_to_remove:
                    try:
                        connection.logout()
                    except:
                        pass
                
                # Similar cleanup for SMTP
                smtp_to_remove = []
                temp_smtp_connections = []
                
                while not self.smtp_pool.empty():
                    try:
                        connection, created_time = self.smtp_pool.get_nowait()
                        if current_time - created_time > self.pool_config.max_idle_time:
                            smtp_to_remove.append(connection)
                        else:
                            temp_smtp_connections.append((connection, created_time))
                    except Empty:
                        break
                
                for conn_tuple in temp_smtp_connections:
                    self.smtp_pool.put(conn_tuple)
                
                for connection in smtp_to_remove:
                    try:
                        connection.quit()
                    except:
                        pass
                
                if imap_to_remove or smtp_to_remove:
                    logger.debug(f"🧹 Pool cleanup: removed {len(imap_to_remove)} IMAP, {len(smtp_to_remove)} SMTP connections")
                
            except Exception as e:
                logger.error(f"❌ Pool maintenance error: {e}")
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        return {
            "account_id": self.account_id,
            "email": self.email,
            "imap": {
                "pool_size": self.imap_pool.qsize(),
                "created_total": self.imap_created,
                "active_connections": self.imap_active,
                "max_connections": self.pool_config.max_connections
            },
            "smtp": {
                "pool_size": self.smtp_pool.qsize(),
                "created_total": self.smtp_created,
                "active_connections": self.smtp_active,
                "max_connections": self.pool_config.max_connections
            }
        }

class ProductionEmailPollingService:
    """Production-ready email polling service with intelligent batching"""
    
    def __init__(self, mongo_url: str, db_name: str):
        self.mongo_url = mongo_url
        self.db_name = db_name
        self.db = None
        self.is_running = False
        
        # Connection pools for each account
        self.connection_pools: Dict[str, ProductionConnectionPool] = {}
        
        # Polling statistics
        self.polling_stats = {
            "total_polls": 0,
            "total_emails_found": 0,
            "total_emails_processed": 0,
            "errors": 0,
            "last_poll_time": 0,
            "average_poll_time": 0
        }
        
        # Thread pool for blocking operations
        self.thread_pool = ThreadPoolExecutor(max_workers=config.email_processing.max_workers)
        
    async def initialize(self):
        """Initialize the polling service"""
        try:
            # Connect to database
            client = AsyncIOMotorClient(self.mongo_url)
            self.db = client[self.db_name]
            
            # Initialize connection pools for active accounts
            await self._initialize_connection_pools()
            
            logger.info("✅ Production email polling service initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize polling service: {e}")
            raise
    
    async def _initialize_connection_pools(self):
        """Initialize connection pools for all active email accounts"""
        try:
            accounts = await self.db.email_accounts.find({"is_active": True}).to_list(1000)
            
            pool_config = ConnectionPoolConfig(
                max_connections=config.email_processing.imap_connection_pool_size,
                min_connections=2,
                connection_timeout=30,
                max_idle_time=config.email_processing.connection_max_age,
                health_check_interval=300  # 5 minutes
            )
            
            for account in accounts:
                try:
                    pool = ProductionConnectionPool(account, pool_config)
                    await pool.initialize()
                    self.connection_pools[account['id']] = pool
                    
                except Exception as e:
                    logger.error(f"❌ Failed to initialize pool for {account['email']}: {e}")
                    continue
            
            logger.info(f"✅ Initialized {len(self.connection_pools)} connection pools")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize connection pools: {e}")
    
    async def start_polling(self):
        """Start the email polling service"""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("🚀 Starting production email polling service")
        
        # Start polling tasks
        polling_tasks = []
        
        # Main polling loop
        polling_tasks.append(asyncio.create_task(self._main_polling_loop()))
        
        # Pool statistics updater
        polling_tasks.append(asyncio.create_task(self._stats_updater()))
        
        # Pool health monitor
        polling_tasks.append(asyncio.create_task(self._pool_health_monitor()))
        
        # Wait for all tasks
        try:
            await asyncio.gather(*polling_tasks)
        except Exception as e:
            logger.error(f"❌ Polling service error: {e}")
        finally:
            self.is_running = False
    
    async def _main_polling_loop(self):
        """Main polling loop with intelligent batching"""
        while self.is_running:
            try:
                start_time = time.time()
                
                # Get all active accounts
                accounts = await self.db.email_accounts.find({"is_active": True}).to_list(1000)
                
                if not accounts:
                    await asyncio.sleep(30)
                    continue
                
                # Process accounts in batches
                batch_size = min(10, len(accounts))
                account_batches = [accounts[i:i + batch_size] for i in range(0, len(accounts), batch_size)]
                
                total_new_emails = 0
                
                for batch in account_batches:
                    batch_tasks = []
                    
                    for account in batch:
                        if account['id'] in self.connection_pools:
                            task = asyncio.create_task(self._poll_account_emails(account))
                            batch_tasks.append(task)
                    
                    # Wait for batch to complete
                    if batch_tasks:
                        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                        
                        # Count new emails found
                        for result in batch_results:
                            if isinstance(result, int):
                                total_new_emails += result
                            elif isinstance(result, Exception):
                                logger.error(f"❌ Polling error: {result}")
                                self.polling_stats["errors"] += 1
                
                # Update statistics
                poll_time = time.time() - start_time
                self.polling_stats["total_polls"] += 1
                self.polling_stats["total_emails_found"] += total_new_emails
                self.polling_stats["last_poll_time"] = poll_time
                
                # Calculate average poll time
                self.polling_stats["average_poll_time"] = (
                    (self.polling_stats["average_poll_time"] * (self.polling_stats["total_polls"] - 1) + poll_time) /
                    self.polling_stats["total_polls"]
                )
                
                if total_new_emails > 0:
                    logger.info(f"📥 Polling cycle completed: {total_new_emails} new emails found in {poll_time:.2f}s")
                
                # Adaptive polling interval based on email volume
                if total_new_emails > 10:
                    await asyncio.sleep(30)  # More frequent polling if high volume
                elif total_new_emails > 0:
                    await asyncio.sleep(60)  # Normal polling
                else:
                    await asyncio.sleep(120)  # Less frequent if no emails
                
            except Exception as e:
                logger.error(f"❌ Main polling loop error: {e}")
                self.polling_stats["errors"] += 1
                await asyncio.sleep(60)
    
    async def _poll_account_emails(self, account: Dict[str, Any]) -> int:
        """Poll emails for a specific account"""
        account_id = account['id']
        new_emails_count = 0
        
        try:
            pool = self.connection_pools.get(account_id)
            if not pool:
                logger.warning(f"⚠️ No connection pool for account {account['email']}")
                return 0
            
            # Get IMAP connection from pool
            imap_connection = await pool.get_imap_connection()
            if not imap_connection:
                logger.warning(f"⚠️ Failed to get IMAP connection for {account['email']}")
                return 0
            
            try:
                # Get UID validity and last UID
                last_uid = account.get('last_uid', 0)
                uidvalidity = account.get('uidvalidity', None)
                
                # Check UID validity
                status, uidvalidity_data = imap_connection.response('UIDVALIDITY')
                current_uidvalidity = uidvalidity_data[0].decode() if uidvalidity_data else None
                
                if uidvalidity != current_uidvalidity:
                    # UID validity changed, reset last UID
                    last_uid = 0
                    await self.db.email_accounts.update_one(
                        {"id": account_id},
                        {"$set": {"uidvalidity": current_uidvalidity, "last_uid": 0}}
                    )
                    logger.info(f"🔄 UID validity changed for {account['email']}, reset last UID")
                
                # Search for new emails
                search_criteria = f"UID {last_uid + 1}:*" if last_uid > 0 else "ALL"
                status, message_ids = imap_connection.search(None, search_criteria)
                
                if status != 'OK' or not message_ids[0]:
                    return 0
                
                uid_list = message_ids[0].split()
                if not uid_list:
                    return 0
                
                # Process emails in batches
                email_batch = []
                batch_size = 20  # Process 20 emails at a time
                
                for uid in uid_list:
                    uid_int = int(uid)
                    if uid_int <= last_uid:
                        continue
                    
                    # Fetch email data
                    email_data = await self._fetch_email_data(imap_connection, uid, account)
                    if email_data:
                        email_batch.append(email_data)
                        new_emails_count += 1
                        
                        # Process batch when full
                        if len(email_batch) >= batch_size:
                            await self._process_email_batch(email_batch)
                            email_batch = []
                
                # Process remaining emails
                if email_batch:
                    await self._process_email_batch(email_batch)
                
                # Update last UID
                if uid_list:
                    new_last_uid = int(uid_list[-1])
                    await self.db.email_accounts.update_one(
                        {"id": account_id},
                        {"$set": {
                            "last_uid": new_last_uid,
                            "last_polled": datetime.utcnow()
                        }}
                    )
                
                return new_emails_count
                
            finally:
                # Return connection to pool
                pool.return_imap_connection(imap_connection)
                
        except Exception as e:
            logger.error(f"❌ Error polling account {account['email']}: {e}")
            return 0
    
    async def _fetch_email_data(self, imap_connection: imaplib.IMAP4_SSL, uid: bytes, account: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Fetch email data from IMAP"""
        try:
            # Fetch email
            status, msg_data = imap_connection.fetch(uid, '(RFC822)')
            if status != 'OK' or not msg_data:
                return None
            
            # Parse email
            email_message = email.message_from_bytes(msg_data[0][1])
            
            # Extract basic information
            subject = self._decode_header(email_message.get('Subject', ''))
            sender = self._decode_header(email_message.get('From', ''))
            recipient = self._decode_header(email_message.get('To', ''))
            message_id = email_message.get('Message-ID', f"generated-{uuid.uuid4()}")
            
            # Get body
            body, body_html = self._extract_email_body(email_message)
            
            # Extract thread information
            thread_id = email_message.get('In-Reply-To', message_id)
            references = email_message.get('References', '')
            in_reply_to = email_message.get('In-Reply-To', '')
            
            # Parse date
            date_str = email_message.get('Date', '')
            received_at = self._parse_email_date(date_str)
            
            return {
                "id": str(uuid.uuid4()),
                "account_id": account['id'],
                "message_id": message_id,
                "thread_id": thread_id,
                "subject": subject,
                "sender": sender,
                "recipient": recipient,
                "body": body,
                "body_html": body_html,
                "received_at": received_at,
                "in_reply_to": in_reply_to,
                "references": references,
                "status": "new",
                "intents": [],
                "draft": "",
                "draft_html": "",
                "validation_result": None,
                "processed_at": None,
                "sent_at": None,
                "error": None,
                "created_at": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"❌ Error fetching email data: {e}")
            return None
    
    def _decode_header(self, header: str) -> str:
        """Decode email header"""
        if not header:
            return ""
        
        try:
            decoded_parts = decode_header(header)
            decoded_string = ""
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_string += part.decode(encoding)
                    else:
                        decoded_string += part.decode('utf-8', errors='ignore')
                else:
                    decoded_string += part
            
            return decoded_string
            
        except Exception:
            return header
    
    def _extract_email_body(self, email_message) -> Tuple[str, str]:
        """Extract plain text and HTML body from email"""
        body = ""
        body_html = ""
        
        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    
                    if "attachment" not in content_disposition:
                        if content_type == "text/plain":
                            charset = part.get_content_charset() or 'utf-8'
                            body = part.get_payload(decode=True).decode(charset, errors='ignore')
                        elif content_type == "text/html":
                            charset = part.get_content_charset() or 'utf-8'
                            body_html = part.get_payload(decode=True).decode(charset, errors='ignore')
            else:
                content_type = email_message.get_content_type()
                charset = email_message.get_content_charset() or 'utf-8'
                payload = email_message.get_payload(decode=True)
                
                if isinstance(payload, bytes):
                    if content_type == "text/html":
                        body_html = payload.decode(charset, errors='ignore')
                    else:
                        body = payload.decode(charset, errors='ignore')
                else:
                    body = str(payload)
            
            # Clean up body text
            if body:
                body = EmailReplyParser.parse_reply(body)
                body = re.sub(r'\n\s*\n', '\n\n', body.strip())
            
            return body, body_html
            
        except Exception as e:
            logger.error(f"❌ Error extracting email body: {e}")
            return "", ""
    
    def _parse_email_date(self, date_str: str) -> datetime:
        """Parse email date string"""
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except Exception:
            return datetime.utcnow()
    
    async def _process_email_batch(self, email_batch: List[Dict[str, Any]]):
        """Process a batch of emails efficiently"""
        try:
            if not email_batch:
                return
            
            # Save emails to database first
            await self.db.emails.insert_many(email_batch)
            
            # Process through enhanced email processor
            if enhanced_email_processor:
                result = await enhanced_email_processor.process_email_batch(email_batch)
                self.polling_stats["total_emails_processed"] += result.successful_count
                
                logger.debug(f"📧 Processed batch of {len(email_batch)} emails: {result.successful_count} successful, {result.cached_count} cached")
            
        except Exception as e:
            logger.error(f"❌ Error processing email batch: {e}")
    
    async def _stats_updater(self):
        """Background task to update polling statistics"""
        while self.is_running:
            try:
                # Update statistics in Redis
                if queue_manager.redis_async:
                    stats_with_pools = {
                        **self.polling_stats,
                        "connection_pools": {
                            pool_id: pool.get_pool_stats() 
                            for pool_id, pool in self.connection_pools.items()
                        },
                        "timestamp": time.time()
                    }
                    
                    await queue_manager.redis_async.hset(
                        "polling_stats", 
                        "current", 
                        json.dumps(stats_with_pools)
                    )
                
                await asyncio.sleep(60)  # Update every minute
                
            except Exception as e:
                logger.error(f"❌ Stats updater error: {e}")
                await asyncio.sleep(60)
    
    async def _pool_health_monitor(self):
        """Monitor connection pool health"""
        while self.is_running:
            try:
                unhealthy_pools = []
                
                for account_id, pool in self.connection_pools.items():
                    stats = pool.get_pool_stats()
                    
                    # Check if pool is healthy
                    if stats["imap"]["active_connections"] == 0 and stats["smtp"]["active_connections"] == 0:
                        unhealthy_pools.append(account_id)
                
                if unhealthy_pools:
                    logger.warning(f"⚠️ Unhealthy connection pools detected: {len(unhealthy_pools)}")
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"❌ Pool health monitor error: {e}")
                await asyncio.sleep(300)
    
    def stop_polling(self):
        """Stop the polling service"""
        self.is_running = False
        logger.info("🛑 Stopping production email polling service")
    
    def get_polling_stats(self) -> Dict[str, Any]:
        """Get comprehensive polling statistics"""
        return {
            **self.polling_stats,
            "is_running": self.is_running,
            "active_pools": len(self.connection_pools),
            "connection_pool_stats": {
                pool_id: pool.get_pool_stats() 
                for pool_id, pool in self.connection_pools.items()
            }
        }

# Global instance
production_polling_service = None

def get_production_polling_service(mongo_url: str, db_name: str) -> ProductionEmailPollingService:
    """Get or create the production polling service"""
    global production_polling_service
    
    if not production_polling_service:
        production_polling_service = ProductionEmailPollingService(mongo_url, db_name)
    
    return production_polling_service