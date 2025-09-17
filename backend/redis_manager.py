"""
Redis connection manager and queue system for production-scale email processing
"""
import redis
import aioredis
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import time

from config import config

logger = logging.getLogger(__name__)

class QueueNames(Enum):
    """Queue names for different processing tasks"""
    EMAIL_PROCESSING = "email_processing"
    INTENT_CLASSIFICATION = "intent_classification"
    DRAFT_GENERATION = "draft_generation"
    EMAIL_VALIDATION = "email_validation"
    EMAIL_SENDING = "email_sending"
    CALENDAR_PROCESSING = "calendar_processing"
    HIGH_PRIORITY = "high_priority"
    RETRY_QUEUE = "retry_queue"
    DEAD_LETTER = "dead_letter"

@dataclass
class QueueTask:
    """Represents a task in the queue"""
    id: str
    queue_name: str
    task_type: str
    payload: Dict[str, Any]
    priority: int = 0
    max_retries: int = 3
    current_retry: int = 0
    created_at: float = None
    scheduled_at: float = None
    expires_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.scheduled_at is None:
            self.scheduled_at = time.time()
        if self.expires_at is None:
            self.expires_at = time.time() + 3600  # 1 hour default expiry

class RedisConnectionManager:
    """Manages Redis connections for high-concurrency operations"""
    
    def __init__(self):
        self.redis_sync: Optional[redis.Redis] = None
        self.redis_async: Optional[aioredis.Redis] = None
        self.connection_pool: Optional[redis.ConnectionPool] = None
        self.async_connection_pool: Optional[aioredis.ConnectionPool] = None
        
    async def initialize(self):
        """Initialize Redis connections"""
        try:
            # Synchronous connection pool
            self.connection_pool = redis.ConnectionPool(
                host=config.redis.host,
                port=config.redis.port,
                password=config.redis.password if config.redis.password else None,
                db=config.redis.db,
                max_connections=config.redis.max_connections,
                socket_keepalive=config.redis.socket_keepalive,
                socket_keepalive_options=config.redis.socket_keepalive_options,
                decode_responses=True
            )
            
            self.redis_sync = redis.Redis(connection_pool=self.connection_pool)
            
            # Async connection pool
            self.redis_async = aioredis.from_url(
                config.redis.url,
                max_connections=config.redis.max_connections,
                decode_responses=True
            )
            
            # Test connections
            await self._test_connections()
            logger.info("✅ Redis connections initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Redis connections: {e}")
            raise
    
    async def _test_connections(self):
        """Test Redis connections"""
        # Test sync connection
        self.redis_sync.ping()
        
        # Test async connection
        await self.redis_async.ping()
        
        logger.info("✅ Redis connection tests passed")
    
    async def close(self):
        """Close Redis connections"""
        if self.redis_async:
            await self.redis_async.close()
        if self.connection_pool:
            self.connection_pool.disconnect()

class ProductionQueueManager:
    """High-performance queue manager for email processing"""
    
    def __init__(self, redis_manager: RedisConnectionManager):
        self.redis_manager = redis_manager
        self.redis = None
        self.redis_async = None
        
    async def initialize(self):
        """Initialize queue manager"""
        await self.redis_manager.initialize()
        self.redis = self.redis_manager.redis_sync
        self.redis_async = self.redis_manager.redis_async
        
        # Initialize queue monitoring
        await self._initialize_queue_monitoring()
        logger.info("✅ Production queue manager initialized")
    
    async def _initialize_queue_monitoring(self):
        """Initialize queue monitoring and cleanup tasks"""
        # Set up queue metrics
        for queue_name in QueueNames:
            await self.redis_async.hset("queue_metrics", f"{queue_name.value}_processed", 0)
            await self.redis_async.hset("queue_metrics", f"{queue_name.value}_failed", 0)
    
    async def enqueue_task(self, task: QueueTask) -> bool:
        """Enqueue a task with priority support"""
        try:
            task_data = asdict(task)
            task_json = json.dumps(task_data)
            
            # Add to priority queue (sorted set) and regular queue
            pipe = self.redis_async.pipeline()
            
            # Priority queue (for sorting)
            await pipe.zadd(f"priority:{task.queue_name}", {task.id: task.priority})
            
            # Task data storage
            await pipe.hset("tasks", task.id, task_json)
            
            # Queue for processing (list for FIFO within same priority)
            await pipe.lpush(f"queue:{task.queue_name}", task.id)
            
            # Metrics
            await pipe.hincrby("queue_metrics", f"{task.queue_name}_queued", 1)
            
            await pipe.execute()
            
            logger.debug(f"✅ Task {task.id} enqueued to {task.queue_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to enqueue task {task.id}: {e}")
            return False
    
    async def enqueue_batch(self, tasks: List[QueueTask]) -> int:
        """Enqueue multiple tasks efficiently"""
        if not tasks:
            return 0
        
        try:
            pipe = self.redis_async.pipeline()
            
            for task in tasks:
                task_data = asdict(task)
                task_json = json.dumps(task_data)
                
                # Priority queue
                await pipe.zadd(f"priority:{task.queue_name}", {task.id: task.priority})
                
                # Task data
                await pipe.hset("tasks", task.id, task_json)
                
                # Queue
                await pipe.lpush(f"queue:{task.queue_name}", task.id)
            
            # Update metrics
            queue_counts = {}
            for task in tasks:
                queue_counts[task.queue_name] = queue_counts.get(task.queue_name, 0) + 1
            
            for queue_name, count in queue_counts.items():
                await pipe.hincrby("queue_metrics", f"{queue_name}_queued", count)
            
            await pipe.execute()
            
            logger.info(f"✅ Batch enqueued {len(tasks)} tasks")
            return len(tasks)
            
        except Exception as e:
            logger.error(f"❌ Failed to enqueue batch: {e}")
            return 0
    
    async def dequeue_task(self, queue_name: str, timeout: int = 10) -> Optional[QueueTask]:
        """Dequeue a task with priority support"""
        try:
            # Get highest priority task ID
            priority_result = await self.redis_async.zrevrange(
                f"priority:{queue_name}", 0, 0, withscores=True
            )
            
            if not priority_result:
                # Fall back to regular queue
                task_id = await self.redis_async.brpop(f"queue:{queue_name}", timeout=timeout)
                if not task_id:
                    return None
                task_id = task_id[1]
            else:
                task_id = priority_result[0][0]
                # Remove from priority queue
                await self.redis_async.zrem(f"priority:{queue_name}", task_id)
                # Remove from regular queue
                await self.redis_async.lrem(f"queue:{queue_name}", 1, task_id)
            
            # Get task data
            task_json = await self.redis_async.hget("tasks", task_id)
            if not task_json:
                logger.warning(f"⚠️ Task {task_id} not found in task storage")
                return None
            
            task_data = json.loads(task_json)
            task = QueueTask(**task_data)
            
            logger.debug(f"✅ Task {task.id} dequeued from {queue_name}")
            return task
            
        except Exception as e:
            logger.error(f"❌ Failed to dequeue task from {queue_name}: {e}")
            return None
    
    async def dequeue_batch(self, queue_name: str, batch_size: int = 10) -> List[QueueTask]:
        """Dequeue multiple tasks for batch processing"""
        tasks = []
        
        try:
            # Get batch of task IDs
            task_ids = await self.redis_async.lrange(f"queue:{queue_name}", -batch_size, -1)
            
            if not task_ids:
                return tasks
            
            # Remove from queue
            pipe = self.redis_async.pipeline()
            for task_id in task_ids:
                await pipe.lrem(f"queue:{queue_name}", 1, task_id)
                await pipe.zrem(f"priority:{queue_name}", task_id)
            
            await pipe.execute()
            
            # Get task data
            if task_ids:
                task_data_list = await self.redis_async.hmget("tasks", *task_ids)
                
                for task_json in task_data_list:
                    if task_json:
                        try:
                            task_data = json.loads(task_json)
                            task = QueueTask(**task_data)
                            tasks.append(task)
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to parse task data: {e}")
            
            logger.info(f"✅ Dequeued batch of {len(tasks)} tasks from {queue_name}")
            return tasks
            
        except Exception as e:
            logger.error(f"❌ Failed to dequeue batch from {queue_name}: {e}")
            return tasks
    
    async def complete_task(self, task: QueueTask):
        """Mark task as completed and clean up"""
        try:
            # Remove task data
            await self.redis_async.hdel("tasks", task.id)
            
            # Update metrics
            await self.redis_async.hincrby("queue_metrics", f"{task.queue_name}_processed", 1)
            
            logger.debug(f"✅ Task {task.id} completed")
            
        except Exception as e:
            logger.error(f"❌ Failed to complete task {task.id}: {e}")
    
    async def retry_task(self, task: QueueTask, delay_seconds: int = 0) -> bool:
        """Retry a failed task with exponential backoff"""
        try:
            if task.current_retry >= task.max_retries:
                # Move to dead letter queue
                await self._move_to_dead_letter(task)
                return False
            
            task.current_retry += 1
            
            if delay_seconds > 0:
                task.scheduled_at = time.time() + delay_seconds
                # Add to delayed queue
                await self.redis_async.zadd("delayed_tasks", {task.id: task.scheduled_at})
            
            # Re-enqueue
            await self.enqueue_task(task)
            
            logger.info(f"🔄 Task {task.id} scheduled for retry {task.current_retry}/{task.max_retries}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to retry task {task.id}: {e}")
            return False
    
    async def _move_to_dead_letter(self, task: QueueTask):
        """Move failed task to dead letter queue"""
        try:
            dead_letter_task = QueueTask(
                id=task.id,
                queue_name=QueueNames.DEAD_LETTER.value,
                task_type=task.task_type,
                payload=task.payload,
                priority=0,
                max_retries=0,
                current_retry=task.current_retry
            )
            
            await self.enqueue_task(dead_letter_task)
            await self.redis_async.hincrby("queue_metrics", f"{task.queue_name}_failed", 1)
            
            logger.warning(f"💀 Task {task.id} moved to dead letter queue after {task.current_retry} retries")
            
        except Exception as e:
            logger.error(f"❌ Failed to move task {task.id} to dead letter queue: {e}")
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get comprehensive queue statistics"""
        try:
            stats = {}
            
            # Queue lengths
            for queue_name in QueueNames:
                queue_len = await self.redis_async.llen(f"queue:{queue_name.value}")
                priority_len = await self.redis_async.zcard(f"priority:{queue_name.value}")
                stats[f"{queue_name.value}_length"] = queue_len
                stats[f"{queue_name.value}_priority_length"] = priority_len
            
            # Metrics
            metrics = await self.redis_async.hgetall("queue_metrics")
            stats.update(metrics)
            
            # System info
            stats["redis_memory_usage"] = await self.redis_async.memory_usage("queue_metrics") or 0
            stats["active_connections"] = len(self.redis_manager.connection_pool._available_connections)
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get queue stats: {e}")
            return {}
    
    async def process_delayed_tasks(self):
        """Process tasks that are ready from the delayed queue"""
        try:
            current_time = time.time()
            
            # Get ready tasks
            ready_tasks = await self.redis_async.zrangebyscore(
                "delayed_tasks", 0, current_time, withscores=True
            )
            
            if not ready_tasks:
                return
            
            # Remove from delayed queue and re-enqueue
            pipe = self.redis_async.pipeline()
            
            for task_id, _ in ready_tasks:
                await pipe.zrem("delayed_tasks", task_id)
            
            await pipe.execute()
            
            # Get task data and re-enqueue
            if ready_tasks:
                task_ids = [task_id for task_id, _ in ready_tasks]
                task_data_list = await self.redis_async.hmget("tasks", *task_ids)
                
                for task_json in task_data_list:
                    if task_json:
                        try:
                            task_data = json.loads(task_json)
                            task = QueueTask(**task_data)
                            task.scheduled_at = time.time()
                            await self.enqueue_task(task)
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to process delayed task: {e}")
            
            logger.info(f"✅ Processed {len(ready_tasks)} delayed tasks")
            
        except Exception as e:
            logger.error(f"❌ Failed to process delayed tasks: {e}")

# Global instances
redis_manager = RedisConnectionManager()
queue_manager = ProductionQueueManager(redis_manager)