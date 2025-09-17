"""
Enhanced Email Processing System for Production Scale
Handles 50k+ emails with intelligent batching, caching, and parallel processing
"""
import asyncio
import logging
import time
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json

from config import config
from redis_manager import queue_manager, QueueNames, QueueTask
from cache_manager import cache_manager
from api_rotation_manager import api_rotation_manager, APIProvider

logger = logging.getLogger(__name__)

@dataclass
class BatchProcessingResult:
    """Result of batch processing"""
    processed_count: int
    successful_count: int
    failed_count: int
    cached_count: int
    processing_time: float
    errors: List[str]

class EnhancedEmailProcessor:
    """Production-ready email processor with intelligent batching and caching"""
    
    def __init__(self, db_client):
        self.db = db_client
        self.processing_stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "cached_hits": 0,
            "avg_processing_time": 0.0
        }
        
        # Processing pools
        self.thread_pool = ThreadPoolExecutor(max_workers=config.email_processing.max_workers)
        
        # Batch processing settings
        self.batch_size = config.email_processing.batch_size
        self.max_concurrent_batches = config.email_processing.max_workers // 2
        
    async def initialize(self):
        """Initialize the enhanced email processor"""
        try:
            # Ensure dependencies are initialized
            await queue_manager.initialize()
            await cache_manager.initialize()
            await api_rotation_manager.initialize()
            
            # Start background workers
            await self._start_background_workers()
            
            logger.info("✅ Enhanced email processor initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize enhanced email processor: {e}")
            raise
    
    async def _start_background_workers(self):
        """Start background worker processes"""
        # Start different types of workers
        worker_tasks = []
        
        # Intent classification workers
        for i in range(3):
            task = asyncio.create_task(self._intent_classification_worker(f"intent_worker_{i}"))
            worker_tasks.append(task)
        
        # Draft generation workers
        for i in range(2):
            task = asyncio.create_task(self._draft_generation_worker(f"draft_worker_{i}"))
            worker_tasks.append(task)
        
        # Validation workers
        for i in range(2):
            task = asyncio.create_task(self._validation_worker(f"validation_worker_{i}"))
            worker_tasks.append(task)
        
        # Email sending worker
        task = asyncio.create_task(self._email_sending_worker("sending_worker"))
        worker_tasks.append(task)
        
        # Stats updater
        task = asyncio.create_task(self._stats_updater())
        worker_tasks.append(task)
        
        logger.info(f"✅ Started {len(worker_tasks)} background workers")
    
    async def process_email_batch(self, email_batch: List[Dict[str, Any]]) -> BatchProcessingResult:
        """Process a batch of emails efficiently"""
        start_time = time.time()
        processed_count = 0
        successful_count = 0
        failed_count = 0
        cached_count = 0
        errors = []
        
        try:
            # Step 1: Check for cached results and deduplicate
            emails_to_process, cached_results = await self._check_cached_and_deduplicate(email_batch)
            cached_count = len(cached_results)
            
            # Step 2: Batch intent classification for non-cached emails
            if emails_to_process:
                classification_results = await self._batch_classify_intents(emails_to_process)
                
                # Step 3: Enqueue for further processing
                tasks_enqueued = await self._enqueue_processing_tasks(emails_to_process, classification_results)
                successful_count = tasks_enqueued
                failed_count = len(emails_to_process) - tasks_enqueued
            
            processed_count = len(email_batch)
            
            # Update stats
            self.processing_stats["total_processed"] += processed_count
            self.processing_stats["successful"] += successful_count
            self.processing_stats["cached_hits"] += cached_count
            
            processing_time = time.time() - start_time
            self.processing_stats["avg_processing_time"] = (
                (self.processing_stats["avg_processing_time"] * (self.processing_stats["total_processed"] - processed_count) + 
                 processing_time) / self.processing_stats["total_processed"]
            )
            
            logger.info(f"✅ Processed batch: {processed_count} emails, {successful_count} successful, {cached_count} cached, {failed_count} failed in {processing_time:.2f}s")
            
            return BatchProcessingResult(
                processed_count=processed_count,
                successful_count=successful_count,
                failed_count=failed_count,
                cached_count=cached_count,
                processing_time=processing_time,
                errors=errors
            )
            
        except Exception as e:
            error_msg = f"Batch processing failed: {str(e)}"
            errors.append(error_msg)
            logger.error(f"❌ {error_msg}")
            
            return BatchProcessingResult(
                processed_count=len(email_batch),
                successful_count=0,
                failed_count=len(email_batch),
                cached_count=0,
                processing_time=time.time() - start_time,
                errors=errors
            )
    
    async def _check_cached_and_deduplicate(self, email_batch: List[Dict[str, Any]]) -> Tuple[List[Dict], List[Dict]]:
        """Check for cached results and remove duplicates"""
        emails_to_process = []
        cached_results = []
        
        try:
            for email_data in email_batch:
                email_body = email_data.get("body", "")
                email_subject = email_data.get("subject", "")
                
                # Check for cached intent classification
                cached_intents = await cache_manager.get_cached_intent_classification(email_body, email_subject)
                
                if cached_intents:
                    # Update email with cached results
                    email_data["intents"] = cached_intents["intents"]
                    email_data["status"] = "cached_classification"
                    cached_results.append(email_data)
                    
                    # Still need to process draft and validation, so enqueue with lower priority
                    await self._enqueue_cached_email_processing(email_data)
                else:
                    # Check for similar emails
                    similar_result = await cache_manager.check_similar_email(email_body, threshold=0.85)
                    
                    if similar_result:
                        # Use similar email results with modifications
                        email_data["intents"] = similar_result["processing_result"].get("intents", [])
                        email_data["status"] = "similar_cached"
                        cached_results.append(email_data)
                        
                        await self._enqueue_similar_email_processing(email_data, similar_result)
                    else:
                        emails_to_process.append(email_data)
            
            logger.debug(f"Cache check: {len(cached_results)} cached, {len(emails_to_process)} to process")
            return emails_to_process, cached_results
            
        except Exception as e:
            logger.error(f"❌ Error in cache check: {e}")
            return email_batch, []
    
    async def _batch_classify_intents(self, emails: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Batch classify intents for multiple emails"""
        classification_results = {}
        
        try:
            # Extract unique email bodies for embedding
            unique_bodies = {}
            for email in emails:
                body = email.get("body", "")
                if body and body not in unique_bodies:
                    unique_bodies[body] = []
                unique_bodies[body].append(email["id"])
            
            # Check for cached embeddings first
            cached_embeddings = await cache_manager.get_multiple_cached_embeddings(list(unique_bodies.keys()))
            
            # Get embeddings for non-cached bodies
            embeddings_to_fetch = []
            for body in unique_bodies.keys():
                if cached_embeddings.get(body) is None:
                    embeddings_to_fetch.append(body)
            
            # Fetch missing embeddings in parallel
            if embeddings_to_fetch:
                new_embeddings = await self._batch_get_embeddings(embeddings_to_fetch)
                # Cache new embeddings
                if new_embeddings:
                    await cache_manager.cache_multiple_embeddings(new_embeddings)
                # Merge with cached embeddings
                cached_embeddings.update(new_embeddings)
            
            # Get all intents with embeddings once
            intents_data = await self._get_all_intents_with_embeddings()
            
            # Classify each email
            for email in emails:
                body = email.get("body", "")
                email_embedding = cached_embeddings.get(body)
                
                if email_embedding:
                    intents = await self._classify_with_embedding(email_embedding, intents_data)
                    classification_results[email["id"]] = intents
                    
                    # Cache the classification result
                    await cache_manager.cache_intent_classification(
                        body, email.get("subject", ""), intents
                    )
                else:
                    classification_results[email["id"]] = []
            
            logger.debug(f"✅ Batch classified {len(emails)} emails")
            return classification_results
            
        except Exception as e:
            logger.error(f"❌ Batch intent classification failed: {e}")
            return {}
    
    async def _batch_get_embeddings(self, texts: List[str]) -> Dict[str, List[float]]:
        """Get embeddings for multiple texts efficiently"""
        embeddings = {}
        
        try:
            # Process in smaller chunks to avoid API limits
            chunk_size = 10
            for i in range(0, len(texts), chunk_size):
                chunk = texts[i:i + chunk_size]
                
                # Process chunk in parallel
                tasks = []
                for text in chunk:
                    task = asyncio.create_task(api_rotation_manager.make_cohere_request(text))
                    tasks.append((text, task))
                
                # Wait for all tasks in chunk
                for text, task in tasks:
                    try:
                        embedding = await task
                        embeddings[text] = embedding
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to get embedding for text: {str(e)[:100]}")
                
                # Small delay between chunks to respect rate limits
                if i + chunk_size < len(texts):
                    await asyncio.sleep(0.1)
            
            logger.debug(f"✅ Retrieved {len(embeddings)} embeddings")
            return embeddings
            
        except Exception as e:
            logger.error(f"❌ Batch embedding retrieval failed: {e}")
            return {}
    
    async def _get_all_intents_with_embeddings(self) -> List[Dict[str, Any]]:
        """Get all intents with embeddings from database"""
        try:
            intents = await self.db.intents.find({"embedding": {"$exists": True}}).to_list(1000)
            return intents
        except Exception as e:
            logger.error(f"❌ Failed to get intents: {e}")
            return []
    
    async def _classify_with_embedding(self, email_embedding: List[float], intents_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Classify email using precomputed embedding"""
        intent_scores = []
        
        try:
            for intent in intents_data:
                if "embedding" in intent:
                    similarity = self._cosine_similarity(email_embedding, intent["embedding"])
                    if similarity >= intent.get("confidence_threshold", 0.7):
                        intent_scores.append({
                            "intent_id": intent["id"],
                            "name": intent["name"],
                            "description": intent["description"],
                            "system_prompt": intent.get("system_prompt", ""),
                            "confidence": similarity,
                            "is_meeting_related": intent.get("is_meeting_related", False)
                        })
            
            # Return top 3 intents
            intent_scores.sort(key=lambda x: x["confidence"], reverse=True)
            return intent_scores[:3]
            
        except Exception as e:
            logger.error(f"❌ Classification with embedding failed: {e}")
            return []
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        try:
            import math
            dot_product = sum(x * y for x, y in zip(a, b))
            magnitude_a = math.sqrt(sum(x * x for x in a))
            magnitude_b = math.sqrt(sum(x * x for x in b))
            if magnitude_a == 0 or magnitude_b == 0:
                return 0
            return dot_product / (magnitude_a * magnitude_b)
        except Exception:
            return 0
    
    async def _enqueue_processing_tasks(self, emails: List[Dict], classification_results: Dict[str, List[Dict]]) -> int:
        """Enqueue emails for further processing"""
        enqueued_count = 0
        
        try:
            tasks = []
            
            for email in emails:
                email_id = email["id"]
                intents = classification_results.get(email_id, [])
                
                # Update email in database with classification results
                await self.db.emails.update_one(
                    {"id": email_id},
                    {"$set": {
                        "intents": intents,
                        "status": "classified",
                        "classified_at": datetime.utcnow()
                    }}
                )
                
                # Create processing task
                task = QueueTask(
                    id=str(uuid.uuid4()),
                    queue_name=QueueNames.DRAFT_GENERATION.value,
                    task_type="generate_draft",
                    payload={
                        "email_id": email_id,
                        "intents": intents,
                        "priority": self._calculate_email_priority(email, intents)
                    },
                    priority=self._calculate_email_priority(email, intents)
                )
                
                tasks.append(task)
            
            # Enqueue all tasks
            enqueued_count = await queue_manager.enqueue_batch(tasks)
            
            logger.debug(f"✅ Enqueued {enqueued_count} processing tasks")
            return enqueued_count
            
        except Exception as e:
            logger.error(f"❌ Failed to enqueue processing tasks: {e}")
            return 0
    
    def _calculate_email_priority(self, email: Dict, intents: List[Dict]) -> int:
        """Calculate email processing priority"""
        priority = 0
        
        # Base priority on sender importance (could be enhanced with sender scoring)
        sender = email.get("sender", "").lower()
        if any(domain in sender for domain in ["ceo", "president", "director", "urgent"]):
            priority += 10
        
        # Priority based on intents
        for intent in intents:
            if intent.get("is_meeting_related"):
                priority += 5
            if intent.get("confidence", 0) > 0.9:
                priority += 3
        
        # Subject line urgency
        subject = email.get("subject", "").lower()
        if any(word in subject for word in ["urgent", "asap", "immediate", "important"]):
            priority += 5
        
        return min(priority, 100)  # Cap at 100
    
    async def _enqueue_cached_email_processing(self, email_data: Dict):
        """Enqueue cached email for draft generation"""
        try:
            task = QueueTask(
                id=str(uuid.uuid4()),
                queue_name=QueueNames.DRAFT_GENERATION.value,
                task_type="generate_draft_cached",
                payload={
                    "email_id": email_data["id"],
                    "intents": email_data["intents"],
                    "cached": True
                },
                priority=1  # Lower priority for cached items
            )
            
            await queue_manager.enqueue_task(task)
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to enqueue cached email processing: {e}")
    
    async def _enqueue_similar_email_processing(self, email_data: Dict, similar_result: Dict):
        """Enqueue similar email for modified processing"""
        try:
            task = QueueTask(
                id=str(uuid.uuid4()),
                queue_name=QueueNames.DRAFT_GENERATION.value,
                task_type="generate_draft_similar",
                payload={
                    "email_id": email_data["id"],
                    "intents": email_data["intents"],
                    "similar_result": similar_result,
                    "similarity_based": True
                },
                priority=2  # Slightly higher priority than cached
            )
            
            await queue_manager.enqueue_task(task)
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to enqueue similar email processing: {e}")
    
    # Background Worker Methods
    async def _intent_classification_worker(self, worker_name: str):
        """Worker for intent classification tasks"""
        logger.info(f"🟢 Started intent classification worker: {worker_name}")
        
        while True:
            try:
                task = await queue_manager.dequeue_task(QueueNames.INTENT_CLASSIFICATION.value, timeout=30)
                
                if task:
                    await self._process_intent_classification_task(task)
                    await queue_manager.complete_task(task)
                else:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"❌ Intent classification worker {worker_name} error: {e}")
                if 'task' in locals():
                    await queue_manager.retry_task(task, delay_seconds=30)
                await asyncio.sleep(5)
    
    async def _draft_generation_worker(self, worker_name: str):
        """Worker for draft generation tasks"""
        logger.info(f"🟢 Started draft generation worker: {worker_name}")
        
        while True:
            try:
                task = await queue_manager.dequeue_task(QueueNames.DRAFT_GENERATION.value, timeout=30)
                
                if task:
                    await self._process_draft_generation_task(task)
                    await queue_manager.complete_task(task)
                else:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"❌ Draft generation worker {worker_name} error: {e}")
                if 'task' in locals():
                    await queue_manager.retry_task(task, delay_seconds=60)
                await asyncio.sleep(5)
    
    async def _validation_worker(self, worker_name: str):
        """Worker for email validation tasks"""
        logger.info(f"🟢 Started validation worker: {worker_name}")
        
        while True:
            try:
                task = await queue_manager.dequeue_task(QueueNames.EMAIL_VALIDATION.value, timeout=30)
                
                if task:
                    await self._process_validation_task(task)
                    await queue_manager.complete_task(task)
                else:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"❌ Validation worker {worker_name} error: {e}")
                if 'task' in locals():
                    await queue_manager.retry_task(task, delay_seconds=30)
                await asyncio.sleep(5)
    
    async def _email_sending_worker(self, worker_name: str):
        """Worker for email sending tasks"""
        logger.info(f"🟢 Started email sending worker: {worker_name}")
        
        while True:
            try:
                task = await queue_manager.dequeue_task(QueueNames.EMAIL_SENDING.value, timeout=30)
                
                if task:
                    await self._process_email_sending_task(task)
                    await queue_manager.complete_task(task)
                else:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"❌ Email sending worker {worker_name} error: {e}")
                if 'task' in locals():
                    await queue_manager.retry_task(task, delay_seconds=120)
                await asyncio.sleep(5)
    
    async def _process_draft_generation_task(self, task: QueueTask):
        """Process a draft generation task"""
        try:
            payload = task.payload
            email_id = payload["email_id"]
            intents = payload["intents"]
            
            # Get email from database
            email_doc = await self.db.emails.find_one({"id": email_id})
            if not email_doc:
                logger.warning(f"⚠️ Email {email_id} not found for draft generation")
                return
            
            # Check for cached draft
            cached_draft = await cache_manager.get_cached_draft(email_doc["body"], intents)
            
            if cached_draft and not payload.get("force_regenerate", False):
                # Use cached draft
                draft_result = cached_draft
                logger.debug(f"✅ Using cached draft for email {email_id}")
            else:
                # Generate new draft
                draft_result = await self._generate_draft_with_api(email_doc, intents)
                
                # Cache the result
                await cache_manager.cache_draft(email_doc["body"], intents, draft_result)
            
            # Update email in database
            await self.db.emails.update_one(
                {"id": email_id},
                {"$set": {
                    "draft": draft_result["plain_text"],
                    "draft_html": draft_result["html"],
                    "status": "draft_generated",
                    "draft_generated_at": datetime.utcnow()
                }}
            )
            
            # Enqueue for validation
            validation_task = QueueTask(
                id=str(uuid.uuid4()),
                queue_name=QueueNames.EMAIL_VALIDATION.value,
                task_type="validate_draft",
                payload={
                    "email_id": email_id,
                    "draft_result": draft_result,
                    "intents": intents
                },
                priority=task.priority
            )
            
            await queue_manager.enqueue_task(validation_task)
            
        except Exception as e:
            logger.error(f"❌ Draft generation task failed: {e}")
            raise
    
    async def _generate_draft_with_api(self, email_doc: Dict, intents: List[Dict]) -> Dict[str, str]:
        """Generate draft using API rotation manager"""
        try:
            # Get account info
            account = await self.db.email_accounts.find_one({"id": email_doc["account_id"]})
            if not account:
                raise Exception(f"Account not found for email {email_doc['id']}")
            
            # Get enhanced knowledge base context
            kb_data = await self._get_enhanced_knowledge_context(email_doc["body"], intents)
            
            # Build system prompt
            system_prompt = self._build_draft_system_prompt(email_doc, intents, account, kb_data)
            
            # Create messages
            messages = [
                {"role": "user", "content": f"Generate a comprehensive email body response for: {email_doc['body']}"}
            ]
            
            # Generate draft using API rotation manager
            response = await api_rotation_manager.make_groq_request(messages, system_prompt)
            
            # Clean the response
            clean_response = self._clean_draft_response(response)
            
            # Generate HTML version
            html_version = self._generate_html_version(clean_response)
            
            return {
                "plain_text": clean_response,
                "html": html_version,
                "reasoning": f"Used KB items: {kb_data.get('items_count', 0)}, Intents: {', '.join([i['name'] for i in intents])}"
            }
            
        except Exception as e:
            logger.error(f"❌ Draft generation with API failed: {e}")
            raise
    
    def _build_draft_system_prompt(self, email_doc: Dict, intents: List[Dict], account: Dict, kb_data: Dict) -> str:
        """Build comprehensive system prompt for draft generation"""
        intent_descriptions = [f"- {intent['name']}: {intent['description']} (confidence: {intent['confidence']:.2f})" 
                             for intent in intents]
        
        system_prompt = f"""You are Agent A - an email draft generator. Generate ONLY the email body content for a professional reply.

ACCOUNT PERSONA: {account.get('persona', 'Professional and helpful')}

EMAIL CONTEXT:
- Original Subject: {email_doc['subject']}
- From: {email_doc['sender']}
- Body: {email_doc['body']}

IDENTIFIED INTENTS:
{chr(10).join(intent_descriptions) if intent_descriptions else "No specific intents identified"}

{kb_data.get("context", "")}

CRITICAL INSTRUCTIONS:
1. Generate ONLY the email body content - no subject lines, no signatures, no placeholders
2. MUST use information from the knowledge base when relevant
3. Keep response comprehensive but professional (200-400 words when detailed info is needed)
4. Address all identified intents directly using knowledge base information
5. Maintain a {account.get('persona', 'professional')} tone
6. Include actionable next steps where appropriate
7. Start directly with the email content (e.g., "Thank you for your inquiry...")

Generate the email body content now:"""

        return system_prompt
    
    def _clean_draft_response(self, response: str) -> str:
        """Clean the draft response"""
        import re
        
        clean_response = response.strip()
        
        # Remove any <think> tags or reasoning content
        clean_response = re.sub(r'<think>.*?</think>', '', clean_response, flags=re.DOTALL)
        clean_response = re.sub(r'PLAIN_TEXT:|HTML:|Subject:|Re:.*?\n', '', clean_response)
        clean_response = re.sub(r'^-+|^=+', '', clean_response, flags=re.MULTILINE)
        clean_response = clean_response.strip()
        
        return clean_response
    
    def _generate_html_version(self, plain_text: str) -> str:
        """Generate HTML version from plain text"""
        import re
        
        html_version = plain_text.replace('\n\n', '</p><p>').replace('\n', '<br>')
        if html_version and not html_version.startswith('<p>'):
            html_version = f"<p>{html_version}</p>"
        
        # Make links clickable
        url_pattern = r'(https?://[^\s<>"{}|\\^`[\]]+)'
        html_version = re.sub(url_pattern, r'<a href="\1" target="_blank">\1</a>', html_version)
        
        return html_version
    
    async def _get_enhanced_knowledge_context(self, email_body: str, intents: List[Dict]) -> Dict[str, Any]:
        """Get enhanced knowledge base context with caching"""
        try:
            # Create cache key from email body and intents
            context_hash = hashlib.md5(f"{email_body}_{json.dumps(intents, sort_keys=True)}".encode()).hexdigest()
            
            # Check cache first
            cached_context = await cache_manager.get_cached_knowledge_context(context_hash)
            if cached_context:
                return cached_context
            
            # Get email embedding
            email_embedding = await cache_manager.get_cached_embedding(email_body)
            if not email_embedding:
                email_embedding = await api_rotation_manager.make_cohere_request(email_body)
                await cache_manager.cache_embedding(email_body, email_embedding)
            
            # Get knowledge base items
            kb_items = await self.db.knowledge_base.find({"embedding": {"$exists": True}}).to_list(1000)
            
            relevant_items = []
            for item in kb_items:
                if "embedding" in item:
                    similarity = self._cosine_similarity(email_embedding, item["embedding"])
                    if similarity >= 0.5:
                        relevant_items.append({
                            "title": item["title"],
                            "content": item["content"],
                            "tags": item.get("tags", []),
                            "similarity": similarity
                        })
            
            # Sort by similarity and take top 5
            relevant_items.sort(key=lambda x: x["similarity"], reverse=True)
            relevant_items = relevant_items[:5]
            
            # Build context
            if relevant_items:
                context = "RELEVANT KNOWLEDGE BASE INFORMATION:\n"
                for item in relevant_items:
                    context += f"- {item['title']}: {item['content']}\n"
                context += f"\nTags: {', '.join(set([tag for item in relevant_items for tag in item.get('tags', [])]))}\n"
                
                context_data = {
                    "context": context,
                    "items_count": len(relevant_items),
                    "has_relevant_info": True
                }
            else:
                context_data = {
                    "context": "No highly relevant knowledge base items found. Use general professional tone.",
                    "items_count": 0,
                    "has_relevant_info": False
                }
            
            # Cache the result
            await cache_manager.cache_knowledge_context(context_hash, context_data)
            
            return context_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get enhanced knowledge context: {e}")
            return {
                "context": "Error retrieving knowledge base information. Use general professional tone.",
                "items_count": 0,
                "has_relevant_info": False
            }
    
    async def _process_validation_task(self, task: QueueTask):
        """Process an email validation task"""
        try:
            payload = task.payload
            email_id = payload["email_id"]
            draft_result = payload["draft_result"]
            intents = payload["intents"]
            
            # Get email from database
            email_doc = await self.db.emails.find_one({"id": email_id})
            if not email_doc:
                logger.warning(f"⚠️ Email {email_id} not found for validation")
                return
            
            # Validate draft
            validation_result = await self._validate_draft_with_api(email_doc, draft_result, intents)
            
            # Determine final status
            if validation_result["status"] == "PASS":
                final_status = "ready_to_send"
                # Enqueue for sending if auto-send is enabled
                account = await self.db.email_accounts.find_one({"id": email_doc["account_id"]})
                if account and account.get("auto_send", True):
                    send_task = QueueTask(
                        id=str(uuid.uuid4()),
                        queue_name=QueueNames.EMAIL_SENDING.value,
                        task_type="send_email",
                        payload={"email_id": email_id},
                        priority=task.priority
                    )
                    await queue_manager.enqueue_task(send_task)
            else:
                final_status = "needs_redraft"
            
            # Update email in database
            await self.db.emails.update_one(
                {"id": email_id},
                {"$set": {
                    "validation_result": validation_result,
                    "status": final_status,
                    "processed_at": datetime.utcnow()
                }}
            )
            
        except Exception as e:
            logger.error(f"❌ Validation task failed: {e}")
            raise
    
    async def _validate_draft_with_api(self, email_doc: Dict, draft_result: Dict, intents: List[Dict]) -> Dict[str, Any]:
        """Validate draft using API rotation manager"""
        try:
            # Build validation system prompt
            system_prompt = f"""You are Agent B - an email draft validator. Check if the draft correctly addresses the email and uses available information.

ORIGINAL EMAIL:
Subject: {email_doc['subject']}
From: {email_doc['sender']}
Body: {email_doc['body']}

IDENTIFIED INTENTS:
{chr(10).join([f"- {intent['name']}: {intent['description']}" for intent in intents])}

DRAFT TO VALIDATE:
{draft_result['plain_text']}

VALIDATION CRITERIA:
1. Does the draft address each identified intent appropriately?
2. Is the tone appropriate and professional?
3. Are actionable next steps provided where needed?
4. Is the response length appropriate for the inquiry complexity?

Start your response with either "PASS:" or "FAIL:" followed by detailed explanation."""

            messages = [
                {"role": "user", "content": "Please validate this draft response. Start with PASS: or FAIL:"}
            ]
            
            validation_response = await api_rotation_manager.make_groq_request(messages, system_prompt)
            
            # Parse validation response
            is_pass = "PASS:" in validation_response.upper() or validation_response.upper().startswith("PASS")
            
            # Extract feedback
            feedback = validation_response
            if validation_response.startswith("PASS:"):
                feedback = validation_response[5:].strip()
            elif validation_response.startswith("FAIL:"):
                feedback = validation_response[5:].strip()
            
            return {
                "status": "PASS" if is_pass else "FAIL",
                "feedback": feedback,
                "coverage_report": validation_response
            }
            
        except Exception as e:
            logger.error(f"❌ Draft validation with API failed: {e}")
            return {
                "status": "FAIL",
                "feedback": f"Validation failed due to error: {str(e)}",
                "coverage_report": "Error during validation"
            }
    
    async def _process_email_sending_task(self, task: QueueTask):
        """Process an email sending task"""
        try:
            payload = task.payload
            email_id = payload["email_id"]
            
            # Get email and account
            email_doc = await self.db.emails.find_one({"id": email_id})
            if not email_doc:
                logger.warning(f"⚠️ Email {email_id} not found for sending")
                return
            
            account_doc = await self.db.email_accounts.find_one({"id": email_doc["account_id"]})
            if not account_doc:
                logger.warning(f"⚠️ Account not found for email {email_id}")
                return
            
            # Send email (this would use the existing EmailConnection class)
            success = await self._send_email_reply(email_doc, account_doc)
            
            if success:
                # Update status to sent
                await self.db.emails.update_one(
                    {"id": email_id},
                    {"$set": {
                        "status": "sent",
                        "sent_at": datetime.utcnow()
                    }}
                )
                logger.info(f"✅ Email {email_id} sent successfully")
            else:
                # Mark as failed to send
                await self.db.emails.update_one(
                    {"id": email_id},
                    {"$set": {"status": "send_failed"}}
                )
                logger.error(f"❌ Failed to send email {email_id}")
            
        except Exception as e:
            logger.error(f"❌ Email sending task failed: {e}")
            raise
    
    async def _send_email_reply(self, email_doc: Dict, account_doc: Dict) -> bool:
        """Send email reply (placeholder - would use existing EmailConnection)"""
        try:
            # This would integrate with the existing EmailConnection class
            # For now, just simulate sending
            await asyncio.sleep(0.1)  # Simulate sending time
            return True
        except Exception as e:
            logger.error(f"❌ Email sending failed: {e}")
            return False
    
    async def _stats_updater(self):
        """Background task to update processing statistics"""
        while True:
            try:
                # Update processing stats in Redis for monitoring
                stats = {
                    **self.processing_stats,
                    "timestamp": time.time(),
                    "queue_stats": await queue_manager.get_queue_stats(),
                    "cache_stats": await cache_manager.get_cache_stats(),
                    "api_stats": await api_rotation_manager.get_api_stats()
                }
                
                await queue_manager.redis_async.hset("processing_stats", "current", json.dumps(stats))
                
                await asyncio.sleep(60)  # Update every minute
                
            except Exception as e:
                logger.warning(f"⚠️ Stats updater error: {e}")
                await asyncio.sleep(60)
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get comprehensive processing statistics"""
        try:
            base_stats = self.processing_stats.copy()
            
            # Get queue stats
            queue_stats = await queue_manager.get_queue_stats()
            
            # Get cache stats
            cache_stats = await cache_manager.get_cache_stats()
            
            # Get API stats
            api_stats = await api_rotation_manager.get_api_stats()
            
            return {
                "processing": base_stats,
                "queues": queue_stats,
                "cache": cache_stats,
                "api": api_stats,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get processing stats: {e}")
            return self.processing_stats

# This will be initialized in the main server
enhanced_email_processor = None