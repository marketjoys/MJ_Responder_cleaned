# 🚀 Systemd Service Files - Installation Guide

## 📦 What You Have

All systemd service files are located in: `/app/systemd-services/`

### Service Files:
1. ✅ `redis-mj-responder.service` - Redis server
2. ✅ `rq-worker-mj-responder.service` - RQ background worker
3. ✅ `rq-scheduler-mj-responder.service` - RQ scheduler
4. ✅ `backend-mj-responder.service` - Backend API

---

## ⚡ QUICK INSTALL (Recommended)

### Option 1: One-Command Install

```bash
sudo bash /app/systemd-services/quick_start.sh
```

### Option 2: Automated Install Script

```bash
cd /app/systemd-services
sudo bash install_services.sh
```

This will automatically:
- ✅ Copy service files to `/etc/systemd/system/`
- ✅ Enable services (auto-start on boot)
- ✅ Start all services
- ✅ Verify they're running

**That's it! Services will now auto-start on every boot!**

---

## 🔧 MANUAL INSTALL

If you prefer manual control:

### Step 1: Copy Service Files

```bash
sudo cp /app/systemd-services/*.service /etc/systemd/system/
```

### Step 2: Reload Systemd

```bash
sudo systemctl daemon-reload
```

### Step 3: Enable Auto-Start on Boot

```bash
sudo systemctl enable redis-mj-responder.service
sudo systemctl enable rq-worker-mj-responder.service
sudo systemctl enable rq-scheduler-mj-responder.service
sudo systemctl enable backend-mj-responder.service
```

### Step 4: Start Services Now

```bash
# Start in order (Redis first, then workers, then backend)
sudo systemctl start redis-mj-responder.service
sudo systemctl start rq-worker-mj-responder.service
sudo systemctl start rq-scheduler-mj-responder.service
sudo systemctl start backend-mj-responder.service
```

### Step 5: Verify All Running

```bash
sudo systemctl status redis-mj-responder rq-worker-mj-responder rq-scheduler-mj-responder backend-mj-responder
```

Expected: All should show `Active: active (running)`

---

## 📋 DAILY MANAGEMENT COMMANDS

### Check Status
```bash
# All services
sudo systemctl status redis-mj-responder rq-worker-mj-responder rq-scheduler-mj-responder backend-mj-responder

# Single service
sudo systemctl status backend-mj-responder
```

### Start/Stop/Restart

```bash
# Restart all
sudo systemctl restart redis-mj-responder rq-worker-mj-responder rq-scheduler-mj-responder backend-mj-responder

# Restart backend only
sudo systemctl restart backend-mj-responder

# Stop all
sudo systemctl stop redis-mj-responder rq-worker-mj-responder rq-scheduler-mj-responder backend-mj-responder
```

### View Logs

```bash
# Follow logs in real-time
sudo journalctl -u backend-mj-responder -f
sudo journalctl -u rq-worker-mj-responder -f

# Last 50 lines
sudo journalctl -u backend-mj-responder -n 50
```

---

## 🔍 VERIFY INSTALLATION

After installation, run these checks:

### 1. Check if services are enabled (auto-start on boot)
```bash
systemctl is-enabled redis-mj-responder
systemctl is-enabled rq-worker-mj-responder
systemctl is-enabled rq-scheduler-mj-responder
systemctl is-enabled backend-mj-responder
```
✅ All should return: `enabled`

### 2. Check if services are running
```bash
systemctl is-active redis-mj-responder
systemctl is-active rq-worker-mj-responder
systemctl is-active rq-scheduler-mj-responder
systemctl is-active backend-mj-responder
```
✅ All should return: `active`

### 3. Test Redis connection
```bash
redis-cli ping
```
✅ Should return: `PONG`

### 4. Test backend API
```bash
curl http://localhost:8001/api/health
```
✅ Should return backend health status

### 5. Check RQ worker queues
```bash
cd /app/backend
python -c "from redis import Redis; from rq import Queue; r = Redis.from_url('redis://localhost:6379/0'); q = Queue('email-processing', connection=r); print(f'Queue length: {len(q)}')"
```
✅ Should show queue length

---

## ❓ TROUBLESHOOTING

### Service won't start?

1. **Check logs:**
   ```bash
   sudo journalctl -u <service-name> -n 100
   ```

2. **Check service file:**
   ```bash
   sudo systemctl cat <service-name>
   ```

3. **Test manually:**
   ```bash
   # For backend
   cd /app/backend
   /root/.venv/bin/python -m uvicorn server:app --host 0.0.0.0 --port 8001
   
   # For RQ worker
   cd /app/backend
   /root/.venv/bin/python start_worker.py
   ```

### Port already in use?

```bash
# Check what's using port 8001
sudo lsof -i:8001

# Check what's using port 6379
sudo lsof -i:6379
```

### Redis not installed?

```bash
sudo apt-get update
sudo apt-get install -y redis-server
```

---

## 📱 QUICK REFERENCE

| Command | Description |
|---------|-------------|
| `sudo systemctl start <service>` | Start a service |
| `sudo systemctl stop <service>` | Stop a service |
| `sudo systemctl restart <service>` | Restart a service |
| `sudo systemctl status <service>` | Check service status |
| `sudo systemctl enable <service>` | Enable auto-start |
| `sudo systemctl disable <service>` | Disable auto-start |
| `sudo journalctl -u <service> -f` | Follow logs |
| `sudo systemctl daemon-reload` | Reload after editing service files |

### Service Names:
- `redis-mj-responder.service`
- `rq-worker-mj-responder.service`
- `rq-scheduler-mj-responder.service`
- `backend-mj-responder.service`

---

## 🎯 WHAT HAPPENS ON SYSTEM REBOOT?

After you enable the services (Step 3 above), they will **automatically start** when the system boots.

**Boot sequence:**
1. System starts
2. Network comes up
3. MongoDB starts
4. Redis starts
5. RQ Worker starts (depends on Redis)
6. RQ Scheduler starts (depends on Redis)
7. Backend API starts (depends on Redis)

**No manual intervention needed!**

---

## 📚 MORE INFORMATION

- **Full Documentation:** `/app/systemd-services/README.md`
- **Deployment Guide:** `/app/DEPLOYMENT_SETUP_GUIDE.md`
- **Service Files Directory:** `/app/systemd-services/`

---

**Need help? Check the logs first:**
```bash
sudo journalctl -u backend-mj-responder -n 100
```
