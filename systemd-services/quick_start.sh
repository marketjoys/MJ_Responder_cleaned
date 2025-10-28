#!/bin/bash
# Quick Start Script - Install and Start All Services

echo "🚀 MJ Responder - Quick Start"
echo "=============================="
echo ""

# Run the installation script
sudo bash /app/systemd-services/install_services.sh

# Show quick commands
echo ""
echo "📋 Quick Commands:"
echo ""
echo "  Status:    sudo systemctl status redis-mj-responder rq-worker-mj-responder rq-scheduler-mj-responder backend-mj-responder"
echo "  Stop All:  sudo systemctl stop redis-mj-responder rq-worker-mj-responder rq-scheduler-mj-responder backend-mj-responder"
echo "  Start All: sudo systemctl start redis-mj-responder rq-worker-mj-responder rq-scheduler-mj-responder backend-mj-responder"
echo "  Logs:      sudo journalctl -u backend-mj-responder -f"
echo ""
