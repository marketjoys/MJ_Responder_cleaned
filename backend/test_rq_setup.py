#!/usr/bin/env python3
"""Quick test to verify RQ and Redis setup"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from redis import Redis
from rq import Queue

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

try:
    # Test Redis connection
    redis_conn = Redis.from_url(redis_url)
    ping = redis_conn.ping()
    print(f"✅ Redis connection: {'OK' if ping else 'FAILED'}")
    
    # Test Queue creation
    queue = Queue('test-queue', connection=redis_conn)
    print(f"✅ RQ Queue created: {queue.name}")
    
    # Check queue info
    print(f"✅ Queue length: {len(queue)}")
    print(f"✅ Redis info: {redis_conn.info('server')['redis_version']}")
    
    print("\n🎉 All tests passed! Redis and RQ are properly configured.")
    sys.exit(0)
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
