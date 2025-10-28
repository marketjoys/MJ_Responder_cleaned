# Systemd Service Files for MJ Responder

This directory contains systemd service files for auto-starting MJ Responder services on boot.

## 📦 Service Files

1. **redis-mj-responder.service** - Redis server (Port 6379)
2. **rq-worker-mj-responder.service** - RQ background worker
3. **rq-scheduler-mj-responder.service** - RQ scheduler for periodic tasks
4. **backend-mj-responder.service** - FastAPI backend (Port 8001)

## 🚀 Quick Installation (Automated)

Run the installation script:

```bash
sudo bash /app/systemd-services/install_services.sh
```

This script will:
- ✅ Copy all service files to `/etc/systemd/system/`
- ✅ Reload systemd daemon
- ✅ Enable all services (auto-start on boot)
- ✅ Start all services
- ✅ Verify service status

## 🔧 Manual Installation

If you prefer to install manually:

### Step 1: Copy Service Files

```bash
sudo cp /app/systemd-services/*.service /etc/systemd/system/
```

### Step 2: Reload Systemd

```bash
sudo systemctl daemon-reload
```

### Step 3: Enable Services (Auto-start on boot)

```bash
sudo systemctl enable redis-mj-responder.service
sudo systemctl enable rq-worker-mj-responder.service
sudo systemctl enable rq-scheduler-mj-responder.service
sudo systemctl enable backend-mj-responder.service
```

### Step 4: Start Services

```bash
sudo systemctl start redis-mj-responder.service
sudo systemctl start rq-worker-mj-responder.service
sudo systemctl start rq-scheduler-mj-responder.service
sudo systemctl start backend-mj-responder.service
```

### Step 5: Verify Services

```bash
sudo systemctl status redis-mj-responder.service
sudo systemctl status rq-worker-mj-responder.service
sudo systemctl status rq-scheduler-mj-responder.service
sudo systemctl status backend-mj-responder.service
```

## 📋 Service Management Commands

### Check Status

```bash
# Single service
sudo systemctl status redis-mj-responder.service

# All services
sudo systemctl status redis-mj-responder rq-worker-mj-responder rq-scheduler-mj-responder backend-mj-responder
```

### Start Services

```bash
# Single service
sudo systemctl start redis-mj-responder.service

# All services
sudo systemctl start redis-mj-responder rq-worker-mj-responder rq-scheduler-mj-responder backend-mj-responder
```

### Stop Services

```bash
# Single service
sudo systemctl stop redis-mj-responder.service

# All services
sudo systemctl stop redis-mj-responder rq-worker-mj-responder rq-scheduler-mj-responder backend-mj-responder
```

### Restart Services

```bash
# Single service
sudo systemctl restart redis-mj-responder.service

# All services
sudo systemctl restart redis-mj-responder rq-worker-mj-responder rq-scheduler-mj-responder backend-mj-responder
```

### Enable/Disable Auto-start

```bash
# Enable (auto-start on boot)
sudo systemctl enable redis-mj-responder.service

# Disable (do not auto-start on boot)
sudo systemctl disable redis-mj-responder.service
```

### View Logs

```bash
# Follow logs in real-time
sudo journalctl -u redis-mj-responder.service -f
sudo journalctl -u rq-worker-mj-responder.service -f
sudo journalctl -u rq-scheduler-mj-responder.service -f
sudo journalctl -u backend-mj-responder.service -f

# View last 50 lines
sudo journalctl -u redis-mj-responder.service -n 50

# View logs since boot
sudo journalctl -u backend-mj-responder.service -b
```

## 🔍 Service Dependencies

```
MongoDB (System Service)
    ↓
redis-mj-responder.service
    ↓
├── rq-worker-mj-responder.service
├── rq-scheduler-mj-responder.service
└── backend-mj-responder.service
```

- **RQ Worker** requires Redis to be running
- **RQ Scheduler** requires Redis to be running
- **Backend** requires Redis to be running (optional dependency on MongoDB)

## ⚙️ Service Configuration Details

### Redis Service
- **Port:** 6379
- **Bind:** 127.0.0.1 (localhost only)
- **Auto-restart:** Yes (5 second delay)

### RQ Worker Service
- **Queues:** email-processing, follow-up, background
- **Working Directory:** /app/backend
- **Python:** /root/.venv/bin/python
- **Auto-restart:** Yes (5 second delay)

### RQ Scheduler Service
- **Scheduler Interval:** 60 seconds
- **Working Directory:** /app/backend
- **Python:** /root/.venv/bin/python
- **Auto-restart:** Yes (5 second delay)

### Backend Service
- **Host:** 0.0.0.0
- **Port:** 8001
- **Working Directory:** /app/backend
- **Python:** /root/.venv/bin/python
- **Auto-restart:** Yes (5 second delay)

## 🛠️ Troubleshooting

### Service Won't Start

1. Check service status:
```bash
sudo systemctl status <service-name>
```

2. View detailed logs:
```bash
sudo journalctl -u <service-name> -n 100 --no-pager
```

3. Check for configuration errors:
```bash
sudo systemctl cat <service-name>
```

### Common Issues

#### Redis Not Starting
```bash
# Check if Redis is installed
which redis-server

# Check if port 6379 is already in use
sudo lsof -i:6379

# Try starting manually
redis-server --bind 127.0.0.1 --port 6379
```

#### RQ Worker Failing
```bash
# Check Python environment
/root/.venv/bin/python --version

# Check if Redis is accessible
redis-cli ping

# Test worker script manually
cd /app/backend
/root/.venv/bin/python start_worker.py
```

#### Backend Not Starting
```bash
# Check if port 8001 is available
sudo lsof -i:8001

# Check Python dependencies
/root/.venv/bin/pip list | grep uvicorn

# Test backend manually
cd /app/backend
/root/.venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001
```

### Permission Issues

If you get permission errors:

```bash
# Ensure service files have correct permissions
sudo chmod 644 /etc/systemd/system/redis-mj-responder.service
sudo chmod 644 /etc/systemd/system/rq-worker-mj-responder.service
sudo chmod 644 /etc/systemd/system/rq-scheduler-mj-responder.service
sudo chmod 644 /etc/systemd/system/backend-mj-responder.service

# Reload systemd
sudo systemctl daemon-reload
```

## 📊 Monitoring Services

### Check if services are enabled for auto-start:

```bash
systemctl is-enabled redis-mj-responder.service
systemctl is-enabled rq-worker-mj-responder.service
systemctl is-enabled rq-scheduler-mj-responder.service
systemctl is-enabled backend-mj-responder.service
```

Expected output: `enabled`

### Check if services are running:

```bash
systemctl is-active redis-mj-responder.service
systemctl is-active rq-worker-mj-responder.service
systemctl is-active rq-scheduler-mj-responder.service
systemctl is-active backend-mj-responder.service
```

Expected output: `active`

### View service resource usage:

```bash
systemctl status redis-mj-responder.service
systemctl status rq-worker-mj-responder.service
systemctl status rq-scheduler-mj-responder.service
systemctl status backend-mj-responder.service
```

## 🔄 Updating Services

If you modify a service file:

```bash
# 1. Copy updated file
sudo cp /app/systemd-services/<service-name>.service /etc/systemd/system/

# 2. Reload systemd
sudo systemctl daemon-reload

# 3. Restart the service
sudo systemctl restart <service-name>
```

## 🗑️ Removing Services

To remove the services:

```bash
# 1. Stop services
sudo systemctl stop redis-mj-responder rq-worker-mj-responder rq-scheduler-mj-responder backend-mj-responder

# 2. Disable services
sudo systemctl disable redis-mj-responder rq-worker-mj-responder rq-scheduler-mj-responder backend-mj-responder

# 3. Remove service files
sudo rm /etc/systemd/system/redis-mj-responder.service
sudo rm /etc/systemd/system/rq-worker-mj-responder.service
sudo rm /etc/systemd/system/rq-scheduler-mj-responder.service
sudo rm /etc/systemd/system/backend-mj-responder.service

# 4. Reload systemd
sudo systemctl daemon-reload
sudo systemctl reset-failed
```

## ✅ Verification Checklist

After installation, verify:

- [ ] All service files copied to `/etc/systemd/system/`
- [ ] Systemd daemon reloaded
- [ ] All services enabled for auto-start
- [ ] All services currently running
- [ ] Redis responding to `redis-cli ping`
- [ ] Backend accessible on port 8001
- [ ] No errors in service logs
- [ ] Services restart automatically after system reboot

---

**For more information, see:**
- Main documentation: `/app/DEPLOYMENT_SETUP_GUIDE.md`
- Deployment script: `/app/deploy_from_github.sh`
