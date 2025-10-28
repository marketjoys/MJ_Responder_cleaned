# MJ Responder - Deployment Setup Guide

## Overview
This guide documents the auto-start configuration for Redis, RQ Workers, and Backend services for the MJ Responder email automation system.

## Changes Made

### 1. Bug Fix: Modal Closing on Signature Button Click
**Problem:** When adding or updating email accounts, clicking any button in the signature editor (Professional, Simple, Corporate templates, or formatting buttons) would close the modal.

**Root Cause:** Buttons in the `RichTextEditor` component lacked `type="button"` attribute, causing them to default to `type="submit"` and trigger form submission.

**Solution:** Added `type="button"` to all buttons in `/app/frontend/src/components/ui/rich-text-editor.jsx`:
- Template buttons (Professional, Simple, Corporate)
- Formatting toolbar buttons (Bold, Italic, Underline, Link)
- Editor mode toggle buttons (Visual, Text)

**Status:** ✅ FIXED

---

### 2. Supervisor Configuration (Development Environment)
For the development environment (current setup), services are managed by supervisor.

#### Services Configured:
1. **Redis** - `/etc/supervisor/conf.d/redis.conf`
   - Command: `/usr/bin/redis-server --bind 127.0.0.1 --port 6379`
   - Auto-start: Yes
   - Priority: 1

2. **RQ Worker** - `/etc/supervisor/conf.d/rq_worker.conf`
   - Command: `/root/.venv/bin/python /app/backend/start_worker.py`
   - Auto-start: Yes
   - Queues: email-processing, follow-up, background
   - Priority: 10

3. **RQ Scheduler** - `/etc/supervisor/conf.d/rq_scheduler.conf`
   - Command: `/root/.venv/bin/python /app/backend/start_scheduler.py`
   - Auto-start: Yes
   - Priority: 10

4. **Backend** - `/etc/supervisor/conf.d/supervisord.conf`
   - Command: `/root/.venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001 --workers 1 --reload`
   - Auto-start: Yes (already configured)

5. **Frontend** - `/etc/supervisor/conf.d/supervisord.conf`
   - Command: `yarn start`
   - Auto-start: Yes (already configured)

#### Supervisor Management Commands:
```bash
# Check status
sudo supervisorctl status

# Start all services
sudo supervisorctl start all

# Restart specific service
sudo supervisorctl restart redis
sudo supervisorctl restart rq_worker
sudo supervisorctl restart rq_scheduler
sudo supervisorctl restart backend

# View logs
tail -f /var/log/supervisor/redis.out.log
tail -f /var/log/supervisor/rq_worker.out.log
tail -f /var/log/supervisor/rq_scheduler.out.log
tail -f /var/log/supervisor/backend.out.log
```

---

### 3. Production Deployment Script Enhancement
Updated `/app/deploy_from_github.sh` to create systemd service files for production deployment.

#### New Function: `create_systemd_services()`
This function creates and enables systemd services for:
1. **redis-mj-responder.service**
2. **rq-worker-mj-responder.service**
3. **rq-scheduler-mj-responder.service**
4. **backend-mj-responder.service**

#### Systemd Service Features:
- **Auto-start on boot:** All services enabled with `systemctl enable`
- **Auto-restart on failure:** `Restart=always` with 5-second delay
- **Dependency management:** Workers depend on Redis
- **Proper ordering:** Services start in correct order

#### Deployment Script Usage:
```bash
# Clone and deploy from GitHub
./deploy_from_github.sh [target_directory]

# Example
./deploy_from_github.sh /opt/email-automation
```

The script will:
1. Install Redis
2. Clone the repository
3. Install Python/Node dependencies
4. Create systemd service files
5. Enable and start all services
6. Build production frontend
7. Create management scripts

#### Management Scripts Created:
The deployment script creates three helper scripts:

1. **start_services.sh** - Start all services
```bash
./start_services.sh
```

2. **stop_services.sh** - Stop all services
```bash
./stop_services.sh
```

3. **check_status.sh** - Check service status
```bash
./check_status.sh
```

#### Systemd Service Management:
```bash
# Start all services
sudo systemctl start redis-mj-responder rq-worker-mj-responder rq-scheduler-mj-responder backend-mj-responder

# Stop all services
sudo systemctl stop redis-mj-responder rq-worker-mj-responder rq-scheduler-mj-responder backend-mj-responder

# Check status
sudo systemctl status redis-mj-responder
sudo systemctl status rq-worker-mj-responder
sudo systemctl status rq-scheduler-mj-responder
sudo systemctl status backend-mj-responder

# View logs
sudo journalctl -u redis-mj-responder.service -f
sudo journalctl -u rq-worker-mj-responder.service -f
sudo journalctl -u rq-scheduler-mj-responder.service -f
sudo journalctl -u backend-mj-responder.service -f

# Restart a service
sudo systemctl restart backend-mj-responder

# Enable/disable auto-start on boot
sudo systemctl enable backend-mj-responder
sudo systemctl disable backend-mj-responder
```

---

## Architecture

### Service Dependencies:
```
MongoDB (System Service)
    ↓
Redis (Port 6379)
    ↓
├── RQ Worker (Processes background tasks)
├── RQ Scheduler (Schedules periodic tasks)
└── Backend API (Port 8001/9000)
         ↓
    Frontend (Port 3000)
```

### Background Tasks Processed by RQ:
1. **Email Processing** - Email classification, draft generation
2. **Follow-ups** - Automated follow-up email scheduling
3. **Response Detection** - Monitoring for email responses
4. **Calendar Integration** - Meeting detection and calendar event creation

---

## Verification

### Current Status (Development):
```bash
sudo supervisorctl status
```

Expected output:
```
backend                          RUNNING   pid XXX, uptime X:XX:XX
frontend                         RUNNING   pid XXX, uptime X:XX:XX
mongodb                          RUNNING   pid XXX, uptime X:XX:XX
redis                            RUNNING   pid XXX, uptime X:XX:XX
rq_scheduler                     RUNNING   pid XXX, uptime X:XX:XX
rq_worker                        RUNNING   pid XXX, uptime X:XX:XX
```

### Test Redis Connection:
```bash
redis-cli ping
# Expected: PONG
```

### Test RQ Setup:
```bash
cd /app/backend
python test_rq_setup.py
```

Expected output:
```
✅ Redis connection: OK
✅ RQ Queue created: test-queue
✅ Queue length: 0
✅ Redis info: 7.0.15

🎉 All tests passed! Redis and RQ are properly configured.
```

---

## Troubleshooting

### Redis Not Starting:
```bash
# Check if Redis is installed
which redis-server

# Check Redis logs
tail -f /var/log/supervisor/redis.err.log

# Try starting manually
redis-server --bind 127.0.0.1 --port 6379
```

### RQ Worker Issues:
```bash
# Check worker logs
tail -f /var/log/supervisor/rq_worker.out.log

# Check for Python environment issues
/root/.venv/bin/python --version

# Test worker script manually
cd /app/backend
/root/.venv/bin/python start_worker.py
```

### Backend Not Starting:
```bash
# Check backend logs
tail -f /var/log/supervisor/backend.err.log

# Check port availability
lsof -i:8001

# Test backend manually
cd /app/backend
/root/.venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001
```

---

## Production Deployment Checklist

- [ ] Install Redis: `sudo apt-get install -y redis-server`
- [ ] Clone repository from GitHub
- [ ] Install Python dependencies: `pip install -r requirements.txt`
- [ ] Install Node dependencies: `yarn install`
- [ ] Configure `.env` files with API keys
- [ ] Run deployment script: `./deploy_from_github.sh`
- [ ] Verify all systemd services are running
- [ ] Configure web server (Nginx/Apache)
- [ ] Test application functionality
- [ ] Monitor logs for any errors

---

## Files Modified

1. `/app/frontend/src/components/ui/rich-text-editor.jsx` - Fixed modal closing bug
2. `/app/deploy_from_github.sh` - Added systemd service creation
3. `/etc/supervisor/conf.d/redis.conf` - New (development)
4. `/etc/supervisor/conf.d/rq_worker.conf` - New (development)
5. `/etc/supervisor/conf.d/rq_scheduler.conf` - New (development)

---

## Summary

✅ **All services are now configured to auto-start on system boot**
✅ **Modal closing bug fixed**
✅ **Production deployment script enhanced with systemd support**
✅ **Development environment uses supervisor for easy management**
✅ **Production environment uses systemd for robust service management**

---

*Last Updated: $(date)*
*Environment: Development (Supervisor) / Production (Systemd)*
