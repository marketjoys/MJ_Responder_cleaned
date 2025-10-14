#!/usr/bin/env python3
"""
RQ Scheduler starter script
"""
import os
import sys
import time
import logging

# Add backend to path
sys.path.append('/app/backend')

from redis import Redis
from rq_scheduler import Scheduler
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv('/app/backend/.env')

# Create Redis connection
redis_conn = Redis.from_url('redis://localhost:6379/0', decode_responses=False)

# Create scheduler
scheduler = Scheduler(connection=redis_conn, interval=60)

logger.info("✅ RQ Scheduler starting - checking every 60 seconds")

# Run scheduler
try:
    scheduler.run()
except KeyboardInterrupt:
    logger.info("⏹ RQ Scheduler stopped")
except Exception as e:
    logger.error(f"❌ RQ Scheduler error: {e}")
    raise
