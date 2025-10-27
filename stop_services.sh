#!/bin/bash

# Stop All Services Script
# This script stops all Email Automation Application services

echo "🛑 Stopping Email Automation Application Services"
echo "================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Stop Backend
echo -e "\n${YELLOW}Stopping Backend...${NC}"
pkill -f "uvicorn server:app"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Backend stopped${NC}"
else
    echo -e "${YELLOW}⚠️  Backend was not running${NC}"
fi

# Stop RQ Scheduler
echo -e "\n${YELLOW}Stopping RQ Scheduler...${NC}"
pkill -f "start_scheduler.py"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ RQ Scheduler stopped${NC}"
else
    echo -e "${YELLOW}⚠️  RQ Scheduler was not running${NC}"
fi

# Stop RQ Worker
echo -e "\n${YELLOW}Stopping RQ Worker...${NC}"
pkill -f "start_worker.py"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ RQ Worker stopped${NC}"
else
    echo -e "${YELLOW}⚠️  RQ Worker was not running${NC}"
fi

# Check if Redis should be stopped (optional)
read -p "Stop Redis server? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    redis-cli shutdown
    echo -e "${GREEN}✅ Redis stopped${NC}"
fi

echo -e "\n================================================="
echo -e "${GREEN}✅ All services stopped${NC}"
echo -e "================================================="
