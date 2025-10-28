#!/bin/bash

################################################################################
# Systemd Services Installation Script for MJ Responder
# This script installs and enables systemd services for auto-start on boot
################################################################################

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║   MJ Responder - Systemd Services Installation            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}\n"

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Please run as root or with sudo${NC}"
    exit 1
fi

SERVICE_DIR="/app/systemd-services"
SYSTEMD_DIR="/etc/systemd/system"

################################################################################
# Step 1: Copy service files to systemd directory
################################################################################
echo -e "${BLUE}━━━ Step 1: Installing Service Files ━━━${NC}\n"

if [ ! -d "$SERVICE_DIR" ]; then
    echo -e "${RED}❌ Service directory not found: $SERVICE_DIR${NC}"
    exit 1
fi

echo -e "${YELLOW}Copying service files...${NC}"

cp "$SERVICE_DIR/redis-mj-responder.service" "$SYSTEMD_DIR/"
echo -e "${GREEN}✅ redis-mj-responder.service${NC}"

cp "$SERVICE_DIR/rq-worker-mj-responder.service" "$SYSTEMD_DIR/"
echo -e "${GREEN}✅ rq-worker-mj-responder.service${NC}"

cp "$SERVICE_DIR/rq-scheduler-mj-responder.service" "$SYSTEMD_DIR/"
echo -e "${GREEN}✅ rq-scheduler-mj-responder.service${NC}"

cp "$SERVICE_DIR/backend-mj-responder.service" "$SYSTEMD_DIR/"
echo -e "${GREEN}✅ backend-mj-responder.service${NC}"

################################################################################
# Step 2: Reload systemd daemon
################################################################################
echo -e "\n${BLUE}━━━ Step 2: Reloading Systemd Daemon ━━━${NC}\n"
systemctl daemon-reload
echo -e "${GREEN}✅ Systemd daemon reloaded${NC}"

################################################################################
# Step 3: Enable services (auto-start on boot)
################################################################################
echo -e "\n${BLUE}━━━ Step 3: Enabling Services (Auto-start on boot) ━━━${NC}\n"

systemctl enable redis-mj-responder.service
echo -e "${GREEN}✅ redis-mj-responder.service enabled${NC}"

systemctl enable rq-worker-mj-responder.service
echo -e "${GREEN}✅ rq-worker-mj-responder.service enabled${NC}"

systemctl enable rq-scheduler-mj-responder.service
echo -e "${GREEN}✅ rq-scheduler-mj-responder.service enabled${NC}"

systemctl enable backend-mj-responder.service
echo -e "${GREEN}✅ backend-mj-responder.service enabled${NC}"

################################################################################
# Step 4: Start services
################################################################################
echo -e "\n${BLUE}━━━ Step 4: Starting Services ━━━${NC}\n"

echo -e "${YELLOW}Starting Redis...${NC}"
systemctl start redis-mj-responder.service
sleep 2
echo -e "${GREEN}✅ Redis started${NC}"

echo -e "${YELLOW}Starting RQ Worker...${NC}"
systemctl start rq-worker-mj-responder.service
sleep 2
echo -e "${GREEN}✅ RQ Worker started${NC}"

echo -e "${YELLOW}Starting RQ Scheduler...${NC}"
systemctl start rq-scheduler-mj-responder.service
sleep 2
echo -e "${GREEN}✅ RQ Scheduler started${NC}"

echo -e "${YELLOW}Starting Backend API...${NC}"
systemctl start backend-mj-responder.service
sleep 3
echo -e "${GREEN}✅ Backend API started${NC}"

################################################################################
# Step 5: Verify services status
################################################################################
echo -e "\n${BLUE}━━━ Step 5: Verifying Services Status ━━━${NC}\n"

check_service_status() {
    SERVICE_NAME=$1
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo -e "${GREEN}✅ $SERVICE_NAME: RUNNING${NC}"
        return 0
    else
        echo -e "${RED}❌ $SERVICE_NAME: NOT RUNNING${NC}"
        return 1
    fi
}

ALL_OK=true
check_service_status "redis-mj-responder.service" || ALL_OK=false
check_service_status "rq-worker-mj-responder.service" || ALL_OK=false
check_service_status "rq-scheduler-mj-responder.service" || ALL_OK=false
check_service_status "backend-mj-responder.service" || ALL_OK=false

################################################################################
# Summary
################################################################################
echo -e "\n${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
if [ "$ALL_OK" = true ]; then
    echo -e "${BLUE}║${GREEN}          🎉 ALL SERVICES INSTALLED SUCCESSFULLY!          ${BLUE}║${NC}"
else
    echo -e "${BLUE}║${YELLOW}     ⚠️  SOME SERVICES FAILED TO START - CHECK LOGS      ${BLUE}║${NC}"
fi
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"

echo -e "${BLUE}📋 Management Commands:${NC}"
echo -e "  ${YELLOW}View Status:${NC}     systemctl status <service-name>"
echo -e "  ${YELLOW}View Logs:${NC}       journalctl -u <service-name> -f"
echo -e "  ${YELLOW}Restart Service:${NC} systemctl restart <service-name>"
echo -e "  ${YELLOW}Stop Service:${NC}    systemctl stop <service-name>"
echo ""

echo -e "${BLUE}🔧 Service Names:${NC}"
echo -e "  - redis-mj-responder.service"
echo -e "  - rq-worker-mj-responder.service"
echo -e "  - rq-scheduler-mj-responder.service"
echo -e "  - backend-mj-responder.service"
echo ""

echo -e "${BLUE}📝 Quick Log Check:${NC}"
echo -e "  journalctl -u redis-mj-responder.service -n 20 --no-pager"
echo -e "  journalctl -u rq-worker-mj-responder.service -n 20 --no-pager"
echo -e "  journalctl -u rq-scheduler-mj-responder.service -n 20 --no-pager"
echo -e "  journalctl -u backend-mj-responder.service -n 20 --no-pager"
echo ""

if [ "$ALL_OK" = false ]; then
    echo -e "${YELLOW}⚠️  To troubleshoot failed services:${NC}"
    echo -e "  1. Check service status: systemctl status <service-name>"
    echo -e "  2. View detailed logs: journalctl -u <service-name> -n 50"
    echo -e "  3. Verify paths and permissions in service files"
    echo ""
fi

echo -e "${GREEN}✅ Services will automatically start on system boot!${NC}\n"
