#!/usr/bin/env python3
"""
RQ Worker starter script
"""
import os
import sys

# Add backend to path
sys.path.append('/app/backend')

from redis import Redis
from rq import Worker
from dotenv import load_dotenv

# Load environment
load_dotenv('/app/backend/.env')

# Create Redis connection (decode_responses=False for RQ worker compatibility)
redis_conn = Redis.from_url('redis://localhost:6379/0', decode_responses=False)

# Create worker
queues = ['email-processing', 'follow-up', 'background']
worker = Worker(queues, connection=redis_conn)

print(f"✅ RQ Worker starting - listening on queues: {queues}")

# Start working
worker.work()
