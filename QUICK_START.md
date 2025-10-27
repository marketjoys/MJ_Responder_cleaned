# 🚀 Quick Start Guide - Email Automation Application

## For Local Deployment to http://marketautomailer.mj.publicvm.com

### Prerequisites Check
```bash
# Check if required software is installed
redis-server --version    # Should show Redis version
mongod --version         # Should show MongoDB version
python3 --version        # Should show Python 3.11+
node --version           # Should show Node.js 16+
yarn --version           # Should show Yarn version
```

---

## 📦 One-Time Setup

### 1. Install Dependencies
```bash
# Backend dependencies
cd /app/backend
pip install -r requirements.txt

# Frontend dependencies
cd /app/frontend
yarn install
```

### 2. Configure Environment
Edit `/app/backend/.env`:
- Update `CORS_ORIGINS` to include your domain
- Verify `MONGO_URL` and `REDIS_URL`
- Add your API keys (Groq, Cohere, etc.)

Edit `/app/frontend/.env.production`:
- Update `REACT_APP_BACKEND_URL` to point to your backend

---

## 🏃 Running the Application

### Option 1: Use All-in-One Script (Recommended)
```bash
cd /app
./start_all_services.sh
```

This script will:
1. ✅ Check and start Redis
2. ✅ Check MongoDB status
3. ✅ Start RQ Worker
4. ✅ Start RQ Scheduler
5. ✅ Start Backend on port 9000

### Option 2: Manual Start (Step by Step)
```bash
# Terminal 1 - Make sure Redis is running
redis-server

# Terminal 2 - Start RQ Worker
cd /app/backend
python start_worker.py

# Terminal 3 - Start RQ Scheduler
cd /app/backend
python start_scheduler.py

# Terminal 4 - Start Backend
cd /app/backend
./start_backend.sh
# OR
uvicorn server:app --host 0.0.0.0 --port 9000
```

---

## 🎨 Building & Deploying Frontend

### Build Production Version
```bash
cd /app/frontend
./build_production.sh
```

### Deploy to Public Folder
```bash
cd /app/frontend
./deploy_to_public.sh /var/www/html/marketautomailer
# or
./deploy_to_public.sh /usr/share/nginx/html
```

### Manual Deployment
```bash
# Copy build files to your public folder
cp -r /app/frontend/build/* /path/to/public/folder/
```

---

## 🌐 Web Server Configuration

### Using Nginx
```bash
# Copy configuration
sudo cp /app/nginx.conf.example /etc/nginx/sites-available/marketautomailer

# Edit paths and domain name if needed
sudo nano /etc/nginx/sites-available/marketautomailer

# Enable site
sudo ln -s /etc/nginx/sites-available/marketautomailer /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### Using Apache
```bash
# Copy configuration
sudo cp /app/apache.conf.example /etc/apache2/sites-available/marketautomailer.conf

# Edit paths and domain name if needed
sudo nano /etc/apache2/sites-available/marketautomailer.conf

# Enable required modules
sudo a2enmod proxy proxy_http headers rewrite

# Enable site
sudo a2ensite marketautomailer

# Test configuration
sudo apache2ctl configtest

# Restart Apache
sudo systemctl restart apache2
```

---

## ✅ Verify Installation

### Check Services Status
```bash
# Redis
redis-cli ping
# Expected output: PONG

# Backend
curl http://localhost:9000/api/email-providers
# Should return JSON response

# Check running processes
ps aux | grep -E "redis|uvicorn|start_worker|start_scheduler"
```

### Check Logs
```bash
# Backend logs
tail -f /var/log/backend.log

# RQ Worker logs
tail -f /var/log/rq_worker.log

# RQ Scheduler logs
tail -f /var/log/rq_scheduler.log

# Nginx/Apache logs
tail -f /var/log/nginx/marketautomailer-error.log
# or
tail -f /var/log/apache2/marketautomailer-error.log
```

---

## 🛑 Stopping Services

### Use Stop Script
```bash
cd /app
./stop_services.sh
```

### Manual Stop
```bash
# Stop Backend
pkill -f "uvicorn server:app"

# Stop RQ Scheduler
pkill -f "start_scheduler.py"

# Stop RQ Worker
pkill -f "start_worker.py"

# Stop Redis (optional)
redis-cli shutdown
```

---

## 🔧 Troubleshooting

### Backend not starting on port 9000
```bash
# Check if port is already in use
lsof -i:9000

# Kill process using port 9000
kill -9 $(lsof -ti:9000)

# Restart backend
cd /app/backend && ./start_backend.sh
```

### CORS Errors
1. Check `/app/backend/.env` - ensure `CORS_ORIGINS` includes your domain
2. Restart backend: `pkill -f uvicorn && cd /app/backend && ./start_backend.sh`
3. Clear browser cache

### Redis Connection Failed
```bash
# Check if Redis is running
redis-cli ping

# If not running, start it
redis-server --daemonize yes

# Restart RQ workers after Redis is up
pkill -f start_worker.py && cd /app/backend && python start_worker.py &
```

### Frontend Build Fails
```bash
# Clear cache and rebuild
cd /app/frontend
rm -rf node_modules build
yarn install
yarn build
```

---

## 📁 Important File Locations

- Backend Code: `/app/backend/`
- Frontend Code: `/app/frontend/`
- Backend Logs: `/var/log/backend.log`
- RQ Worker Logs: `/var/log/rq_worker.log`
- Environment Config: `/app/backend/.env`
- Frontend Config: `/app/frontend/.env.production`
- Nginx Config: `/app/nginx.conf.example`
- Apache Config: `/app/apache.conf.example`

---

## 🔐 Production Checklist

Before going live:
- [ ] Change `JWT_SECRET_KEY` in `.env`
- [ ] Set specific CORS origins (not "*")
- [ ] Set up HTTPS with SSL certificate
- [ ] Configure firewall rules
- [ ] Set up MongoDB authentication
- [ ] Enable rate limiting
- [ ] Set up automated backups
- [ ] Configure monitoring and alerts
- [ ] Review and update OAuth redirect URIs

---

## 📞 Need Help?

Check the detailed documentation:
- Full Deployment Guide: `/app/DEPLOYMENT_INSTRUCTIONS.md`
- API Documentation: Check backend `/api/docs` endpoint
- Configuration Examples: `/app/nginx.conf.example`, `/app/apache.conf.example`

---

**Last Updated:** October 17, 2025
