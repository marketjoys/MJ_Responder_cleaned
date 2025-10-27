#!/bin/bash

# All-in-One Startup Script for Email Automation Application
# This script starts all required services in the correct order

echo "🚀 Starting Email Automation Application"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Redis is running
echo -e "\n${YELLOW}1. Checking Redis...${NC}"
redis-cli ping > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Redis is running${NC}"
else
    echo -e "${YELLOW}⚠️  Redis is not running. Starting Redis...${NC}"
    redis-server --daemonize yes
    sleep 2
    redis-cli ping > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Redis started successfully${NC}"
    else
        echo -e "${RED}❌ Failed to start Redis. Please start it manually.${NC}"
        exit 1
    fi
fi

# Check if MongoDB is running
echo -e "\n${YELLOW}2. Checking MongoDB...${NC}"
pgrep mongod > /dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ MongoDB is running${NC}"
else
    echo -e "${RED}❌ MongoDB is not running. Please start MongoDB first.${NC}"
    echo "   Start MongoDB with: sudo systemctl start mongod"
    exit 1
fi

# Start RQ Worker
echo -e "\n${YELLOW}3. Starting RQ Worker...${NC}"
cd /app/backend
pkill -f "start_worker.py"
nohup python start_worker.py > /var/log/rq_worker.log 2>&1 &
sleep 2
if pgrep -f "start_worker.py" > /dev/null; then
    echo -e "${GREEN}✅ RQ Worker started (PID: $(pgrep -f 'start_worker.py'))${NC}"
else
    echo -e "${RED}❌ Failed to start RQ Worker${NC}"
fi

# Start RQ Scheduler
echo -e "\n${YELLOW}4. Starting RQ Scheduler...${NC}"
pkill -f "start_scheduler.py"
nohup python start_scheduler.py > /var/log/rq_scheduler.log 2>&1 &
sleep 2
if pgrep -f "start_scheduler.py" > /dev/null; then
    echo -e "${GREEN}✅ RQ Scheduler started (PID: $(pgrep -f 'start_scheduler.py'))${NC}"
else
    echo -e "${RED}❌ Failed to start RQ Scheduler${NC}"
fi

# Start Backend on port 9000
echo -e "\n${YELLOW}5. Starting Backend (Port 9000)...${NC}"
pkill -f "uvicorn server:app"
nohup uvicorn server:app --host 0.0.0.0 --port 9000 > /var/log/backend.log 2>&1 &
sleep 3
if lsof -i:9000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend started on port 9000 (PID: $(lsof -ti:9000))${NC}"
else
    echo -e "${RED}❌ Failed to start Backend${NC}"
fi

# Summary
echo -e "\n=========================================="
echo -e "${GREEN}✅ Application Startup Complete${NC}"
echo -e "=========================================="
echo -e "\n📋 Services Status:"
echo -e "   Redis:        $(redis-cli ping 2>/dev/null || echo 'NOT RUNNING')"
echo -e "   MongoDB:      $(pgrep mongod > /dev/null && echo 'RUNNING' || echo 'NOT RUNNING')"
echo -e "   RQ Worker:    $(pgrep -f 'start_worker.py' > /dev/null && echo 'RUNNING' || echo 'NOT RUNNING')"
echo -e "   RQ Scheduler: $(pgrep -f 'start_scheduler.py' > /dev/null && echo 'RUNNING' || echo 'NOT RUNNING')"
echo -e "   Backend:      $(lsof -i:9000 > /dev/null 2>&1 && echo 'RUNNING on port 9000' || echo 'NOT RUNNING')"

echo -e "\n🌐 Access Points:"
echo -e "   Backend API: http://localhost:9000/api"
echo -e "   Frontend:    Deploy build folder to web server"

echo -e "\n📝 Logs Location:"
echo -e "   RQ Worker:    /var/log/rq_worker.log"
echo -e "   RQ Scheduler: /var/log/rq_scheduler.log"
echo -e "   Backend:      /var/log/backend.log"

echo -e "\n💡 To stop all services, run: ./stop_services.sh"
echo -e "💡 To view logs, use: tail -f /var/log/backend.log"
