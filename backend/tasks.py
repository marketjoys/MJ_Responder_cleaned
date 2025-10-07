"""
Background tasks using Redis Queue (RQ)
Handles email processing, follow-ups, and other async operations
"""
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
from redis import Redis
from rq import Queue, Worker
from rq.job import Job
from rq_scheduler import Scheduler
import pymongo

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis connections
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
# Separate connections needed: scheduler needs decode_responses=False, queues can use True
redis_conn = Redis.from_url(REDIS_URL, decode_responses=True)
redis_conn_scheduler = Redis.from_url(REDIS_URL, decode_responses=False)

# Create queues with different priorities
email_processing_queue = Queue('email-processing', connection=redis_conn)
follow_up_queue = Queue('follow-up', connection=redis_conn)
background_queue = Queue('background', connection=redis_conn)

# Scheduler for periodic tasks (needs decode_responses=False)
scheduler = Scheduler(connection=redis_conn_scheduler, queue=background_queue)

# MongoDB connection for tasks
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
mongo_client = pymongo.MongoClient(MONGO_URL)
db = mongo_client['email_assistant']

# Import after MongoDB is set up
import sys
sys.path.append('/app/backend')


def run_async_task(coro):
    """Helper to run async functions in sync context for RQ"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def process_email_task(email_id: str):
    """
    Background task to process email through AI workflow
    This is the RQ task wrapper for async processing
    """
    logger.info(f"📧 [RQ Task] Starting email processing for: {email_id}")
    
    try:
        # Import here to avoid circular dependencies
        from server import process_email_workflow
        
        # Run the async workflow
        result = run_async_task(process_email_workflow(email_id))
        
        logger.info(f"✅ [RQ Task] Email processing completed for: {email_id}")
        return {"status": "success", "email_id": email_id, "result": result}
    
    except Exception as e:
        logger.error(f"❌ [RQ Task] Error processing email {email_id}: {str(e)}")
        return {"status": "error", "email_id": email_id, "error": str(e)}


def auto_send_email_task(email_id: str):
    """
    Background task to auto-send approved email
    """
    logger.info(f"📤 [RQ Task] Auto-sending email: {email_id}")
    
    try:
        from server import auto_send_email_workflow
        
        result = run_async_task(auto_send_email_workflow(email_id))
        
        logger.info(f"✅ [RQ Task] Email auto-sent: {email_id}")
        return {"status": "success", "email_id": email_id, "result": result}
    
    except Exception as e:
        logger.error(f"❌ [RQ Task] Error auto-sending email {email_id}: {str(e)}")
        return {"status": "error", "email_id": email_id, "error": str(e)}


def create_follow_up_task(email_id: str, account_id: str, user_id: str):
    """
    Background task to create follow-up emails for a sent email
    """
    logger.info(f"📅 [RQ Task] Creating follow-up for email: {email_id}")
    
    try:
        from server import create_follow_up_for_email_workflow
        
        result = run_async_task(
            create_follow_up_for_email_workflow(email_id, account_id, user_id)
        )
        
        logger.info(f"✅ [RQ Task] Follow-up created for email: {email_id}")
        return {"status": "success", "email_id": email_id, "result": result}
    
    except Exception as e:
        logger.error(f"❌ [RQ Task] Error creating follow-up for {email_id}: {str(e)}")
        return {"status": "error", "email_id": email_id, "error": str(e)}


def process_scheduled_follow_ups_task():
    """
    Background task to process and send scheduled follow-up emails
    Runs periodically (every 10 minutes)
    """
    logger.info(f"🔄 [RQ Task] Processing scheduled follow-ups")
    
    try:
        from server import process_scheduled_follow_ups_workflow
        
        result = run_async_task(process_scheduled_follow_ups_workflow())
        
        logger.info(f"✅ [RQ Task] Scheduled follow-ups processed: {result}")
        return {"status": "success", "result": result}
    
    except Exception as e:
        logger.error(f"❌ [RQ Task] Error processing scheduled follow-ups: {str(e)}")
        return {"status": "error", "error": str(e)}


def detect_and_cancel_follow_ups_task():
    """
    Background task to detect responses and cancel follow-ups
    Runs periodically (every 5 minutes)
    """
    logger.info(f"🔍 [RQ Task] Detecting responses and cancelling follow-ups")
    
    try:
        from server import detect_and_cancel_follow_ups_workflow
        
        result = run_async_task(detect_and_cancel_follow_ups_workflow())
        
        logger.info(f"✅ [RQ Task] Response detection completed: {result}")
        return {"status": "success", "result": result}
    
    except Exception as e:
        logger.error(f"❌ [RQ Task] Error detecting responses: {str(e)}")
        return {"status": "error", "error": str(e)}


# Queue helper functions
def enqueue_email_processing(email_id: str, delay: int = 0) -> Job:
    """
    Enqueue email processing task
    
    Args:
        email_id: Email ID to process
        delay: Delay in seconds before processing (default: 0)
    
    Returns:
        RQ Job object
    """
    if delay > 0:
        job = email_processing_queue.enqueue_in(
            timedelta(seconds=delay),
            process_email_task,
            email_id,
            job_timeout='10m',
            failure_ttl='1h',
            result_ttl='1h'
        )
    else:
        job = email_processing_queue.enqueue(
            process_email_task,
            email_id,
            job_timeout='10m',
            failure_ttl='1h',
            result_ttl='1h'
        )
    
    logger.info(f"📋 Enqueued email processing: {email_id} (Job ID: {job.id})")
    return job


def enqueue_auto_send_email(email_id: str, delay: int = 0) -> Job:
    """
    Enqueue auto-send email task
    
    Args:
        email_id: Email ID to send
        delay: Delay in seconds before sending (default: 0)
    
    Returns:
        RQ Job object
    """
    if delay > 0:
        job = email_processing_queue.enqueue_in(
            timedelta(seconds=delay),
            auto_send_email_task,
            email_id,
            job_timeout='5m',
            failure_ttl='1h',
            result_ttl='1h'
        )
    else:
        job = email_processing_queue.enqueue(
            auto_send_email_task,
            email_id,
            job_timeout='5m',
            failure_ttl='1h',
            result_ttl='1h'
        )
    
    logger.info(f"📋 Enqueued auto-send email: {email_id} (Job ID: {job.id})")
    return job


def enqueue_create_follow_up(email_id: str, account_id: str, user_id: str, delay: int = 0) -> Job:
    """
    Enqueue follow-up creation task
    
    Args:
        email_id: Email ID
        account_id: Email account ID
        user_id: User ID
        delay: Delay in seconds before creating (default: 0)
    
    Returns:
        RQ Job object
    """
    if delay > 0:
        job = follow_up_queue.enqueue_in(
            timedelta(seconds=delay),
            create_follow_up_task,
            email_id,
            account_id,
            user_id,
            job_timeout='5m',
            failure_ttl='1h',
            result_ttl='1h'
        )
    else:
        job = follow_up_queue.enqueue(
            create_follow_up_task,
            email_id,
            account_id,
            user_id,
            job_timeout='5m',
            failure_ttl='1h',
            result_ttl='1h'
        )
    
    logger.info(f"📋 Enqueued follow-up creation: {email_id} (Job ID: {job.id})")
    return job


def schedule_periodic_tasks():
    """
    Schedule periodic background tasks
    Call this on application startup
    """
    logger.info("⏰ Scheduling periodic tasks...")
    
    # Clear existing scheduled jobs to avoid duplicates
    for job in scheduler.get_jobs():
        scheduler.cancel(job)
    
    # Schedule follow-up processing every 10 minutes
    scheduler.schedule(
        scheduled_time=datetime.utcnow(),
        func=process_scheduled_follow_ups_task,
        interval=600,  # 10 minutes
        repeat=None,  # Repeat indefinitely
        result_ttl=3600
    )
    logger.info("✅ Scheduled: Process follow-ups (every 10 minutes)")
    
    # Schedule response detection every 5 minutes
    scheduler.schedule(
        scheduled_time=datetime.utcnow(),
        func=detect_and_cancel_follow_ups_task,
        interval=300,  # 5 minutes
        repeat=None,  # Repeat indefinitely
        result_ttl=3600
    )
    logger.info("✅ Scheduled: Detect responses (every 5 minutes)")
    
    logger.info("🎉 All periodic tasks scheduled successfully!")


def get_queue_stats() -> Dict[str, Any]:
    """
    Get statistics for all queues
    
    Returns:
        Dictionary with queue statistics
    """
    return {
        "email_processing": {
            "count": len(email_processing_queue),
            "failed": email_processing_queue.failed_job_registry.count,
            "finished": email_processing_queue.finished_job_registry.count,
            "started": email_processing_queue.started_job_registry.count,
            "scheduled": email_processing_queue.scheduled_job_registry.count
        },
        "follow_up": {
            "count": len(follow_up_queue),
            "failed": follow_up_queue.failed_job_registry.count,
            "finished": follow_up_queue.finished_job_registry.count,
            "started": follow_up_queue.started_job_registry.count,
            "scheduled": follow_up_queue.scheduled_job_registry.count
        },
        "background": {
            "count": len(background_queue),
            "failed": background_queue.failed_job_registry.count,
            "finished": background_queue.finished_job_registry.count,
            "started": background_queue.started_job_registry.count,
            "scheduled": background_queue.scheduled_job_registry.count
        },
        "redis_connected": redis_conn.ping()
    }


if __name__ == "__main__":
    # Run RQ worker when this file is executed directly
    # Usage: python tasks.py
    logger.info("🚀 Starting RQ Worker...")
    
    worker = Worker(
        [email_processing_queue, follow_up_queue, background_queue],
        connection=redis_conn,
        log_job_description=True,
        default_result_ttl=3600,
        default_worker_ttl=1800
    )
    
    logger.info("✅ RQ Worker started and listening for jobs...")
    worker.work(with_scheduler=True)
