# Local Deployment Instructions - Email Automation Application

## Prerequisites
- Python 3.11+
- Node.js 16+ and Yarn
- MongoDB running locally or accessible
- Redis server

---

## Step 1: Install Redis

### For Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install -y redis-server

# Start Redis service
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Verify Redis is running
redis-cli ping
# Should return: PONG
```

### For macOS:
```bash
brew install redis
brew services start redis

# Verify
redis-cli ping
```

### For Windows:
Download Redis from: https://github.com/microsoftarchive/redis/releases
Or use WSL2 with Ubuntu instructions above.

---

## Step 2: Backend Setup

### 2.1 Navigate to Backend Directory
```bash
cd /app/backend
```

### 2.2 Install Python Dependencies
```bash
# Create virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2.3 Configure Environment Variables

Edit `/app/backend/.env` file and update these critical settings:

```bash
# Database
MONGO_URL="mongodb://localhost:27017"
DB_NAME="email_automation_db"

# Redis
REDIS_URL="redis://localhost:6379/0"

# API Keys
GROQ_API_KEY="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"
COHERE_API_KEY="OOMW2C2rBBwTvqIxFRNfT4lJoHPvUQQS0pPLQt8p"

# Security
JWT_SECRET_KEY="your-secret-key-change-in-production-2024"
ENCRYPTION_KEY="XAeVOcl-Es4rFbi04_W-xl3ByDrzQi7VHGwqhe--N6s="

# CORS Origins - IMPORTANT FOR PRODUCTION
CORS_ORIGINS="http://marketautomailer.mj.publicvm.com,http://localhost:3000"

# OAuth Configuration (if using OAuth)
GOOGLE_CLIENT_ID="your-google-client-id"
GOOGLE_CLIENT_SECRET="your-google-client-secret"
GOOGLE_REDIRECT_URI="http://marketautomailer.mj.publicvm.com/oauth/google/callback"

MICROSOFT_CLIENT_ID="your-microsoft-client-id"
MICROSOFT_CLIENT_SECRET="your-microsoft-client-secret"
MICROSOFT_TENANT_ID="common"
MICROSOFT_REDIRECT_URI="http://marketautomailer.mj.publicvm.com/oauth/microsoft/callback"
```

### 2.4 Update Backend Port to 9000

Edit `/app/backend/server.py` - Find the uvicorn run section at the bottom and change port:

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)  # Changed from 8001 to 9000
```

---

## Step 3: Start RQ Workers

### 3.1 Terminal 1 - Start RQ Worker
```bash
cd /app/backend
source venv/bin/activate  # If using virtual environment
python start_worker.py
```

You should see:
```
✅ RQ Worker starting - listening on queues: ['email-processing', 'follow-up', 'background']
*** Listening on email-processing, follow-up, background...
```

### 3.2 Terminal 2 - Start RQ Scheduler
```bash
cd /app/backend
source venv/bin/activate  # If using virtual environment
python start_scheduler.py
```

### 3.3 Terminal 3 - Start Backend Server
```bash
cd /app/backend
source venv/bin/activate  # If using virtual environment
python server.py
```

Or using uvicorn directly:
```bash
uvicorn server:app --host 0.0.0.0 --port 9000 --reload
```

Backend should now be running on: **http://localhost:9000**

---

## Step 4: Frontend Setup & Production Build

### 4.1 Navigate to Frontend Directory
```bash
cd /app/frontend
```

### 4.2 Install Dependencies
```bash
yarn install
```

### 4.3 Configure Frontend Environment

Create/Edit `/app/frontend/.env`:

```bash
# Production Backend URL
REACT_APP_BACKEND_URL=http://localhost:9000/api

# For deployment to marketautomailer.mj.publicvm.com, use:
# REACT_APP_BACKEND_URL=http://marketautomailer.mj.publicvm.com:9000/api
```

### 4.4 Build Production Bundle
```bash
yarn build
```

This will create an optimized production build in `/app/frontend/build/` directory.

### 4.5 Copy Build to Public Folder

```bash
# Copy the entire build folder to your public directory
cp -r /app/frontend/build/* /path/to/your/public/folder/

# Example if deploying to Apache/Nginx:
# sudo cp -r /app/frontend/build/* /var/www/html/
# or
# sudo cp -r /app/frontend/build/* /usr/share/nginx/html/
```

---

## Step 5: Handle CORS Configuration

### 5.1 Update Backend CORS Settings

In `/app/backend/server.py`, find the CORS middleware section and update:

```python
# CORS Configuration
allowed_origins_str = os.environ.get('CORS_ORIGINS', '*')
if allowed_origins_str == '*':
    allowed_origins = ["*"]
else:
    allowed_origins = [origin.strip() for origin in allowed_origins_str.split(',')]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 5.2 For Production, Set Specific Origins

In `/app/backend/.env`:
```bash
CORS_ORIGINS="http://marketautomailer.mj.publicvm.com,http://localhost:3000"
```

---

## Step 6: Web Server Configuration (Optional)

### 6.1 Nginx Configuration Example

Create `/etc/nginx/sites-available/email-automation`:

```nginx
server {
    listen 80;
    server_name marketautomailer.mj.publicvm.com;
    
    # Frontend - Serve static files
    location / {
        root /var/www/html/email-automation;
        index index.html;
        try_files $uri $uri/ /index.html;
    }
    
    # Backend API - Proxy to localhost:9000
    location /api/ {
        proxy_pass http://localhost:9000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers (if needed)
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, PATCH, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization' always;
        
        if ($request_method = OPTIONS) {
            return 204;
        }
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/email-automation /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 6.2 Apache Configuration Example

Create `/etc/apache2/sites-available/email-automation.conf`:

```apache
<VirtualHost *:80>
    ServerName marketautomailer.mj.publicvm.com
    
    # Frontend
    DocumentRoot /var/www/html/email-automation
    <Directory /var/www/html/email-automation>
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted
        
        # React Router support
        RewriteEngine On
        RewriteBase /
        RewriteRule ^index\.html$ - [L]
        RewriteCond %{REQUEST_FILENAME} !-f
        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteRule . /index.html [L]
    </Directory>
    
    # Backend API Proxy
    ProxyPreserveHost On
    ProxyPass /api http://localhost:9000/api
    ProxyPassReverse /api http://localhost:9000/api
    
    # CORS Headers
    Header always set Access-Control-Allow-Origin "*"
    Header always set Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS"
    Header always set Access-Control-Allow-Headers "Content-Type, Authorization"
</VirtualHost>
```

Enable required modules and site:
```bash
sudo a2enmod proxy proxy_http headers rewrite
sudo a2ensite email-automation
sudo systemctl restart apache2
```

---

## Step 7: Process Management (Keep Services Running)

### 7.1 Using Supervisor (Recommended)

Install Supervisor:
```bash
sudo apt-get install supervisor
```

Create configuration files:

**Backend: /etc/supervisor/conf.d/email-backend.conf**
```ini
[program:email-backend]
command=/path/to/venv/bin/python /app/backend/server.py
directory=/app/backend
user=youruser
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/email-backend.err.log
stdout_logfile=/var/log/supervisor/email-backend.out.log
environment=PYTHONUNBUFFERED=1
```

**RQ Worker: /etc/supervisor/conf.d/rq-worker.conf**
```ini
[program:rq-worker]
command=/path/to/venv/bin/python /app/backend/start_worker.py
directory=/app/backend
user=youruser
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/rq-worker.err.log
stdout_logfile=/var/log/supervisor/rq-worker.out.log
environment=PYTHONUNBUFFERED=1
```

**RQ Scheduler: /etc/supervisor/conf.d/rq-scheduler.conf**
```ini
[program:rq-scheduler]
command=/path/to/venv/bin/python /app/backend/start_scheduler.py
directory=/app/backend
user=youruser
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/rq-scheduler.err.log
stdout_logfile=/var/log/supervisor/rq-scheduler.out.log
environment=PYTHONUNBUFFERED=1
```

Reload Supervisor:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl status
```

### 7.2 Using PM2 (Alternative)

```bash
npm install -g pm2

# Start backend
pm2 start /app/backend/server.py --name email-backend --interpreter python3

# Start RQ worker
pm2 start /app/backend/start_worker.py --name rq-worker --interpreter python3

# Start RQ scheduler
pm2 start /app/backend/start_scheduler.py --name rq-scheduler --interpreter python3

# Save configuration
pm2 save
pm2 startup
```

---

## Step 8: Verification

### 8.1 Check Services Status
```bash
# Redis
redis-cli ping

# MongoDB
mongo --eval "db.runCommand({ ping: 1 })"

# Backend API
curl http://localhost:9000/api/email-providers
```

### 8.2 Check Logs
```bash
# Backend logs
tail -f /var/log/supervisor/email-backend.out.log

# RQ Worker logs
tail -f /var/log/supervisor/rq-worker.out.log

# RQ Scheduler logs
tail -f /var/log/supervisor/rq-scheduler.out.log
```

### 8.3 Test Frontend
Open browser and navigate to: `http://marketautomailer.mj.publicvm.com`

---

## Quick Start Commands (Summary)

```bash
# Terminal 1 - Redis (if not running as service)
redis-server

# Terminal 2 - RQ Worker
cd /app/backend && python start_worker.py

# Terminal 3 - RQ Scheduler
cd /app/backend && python start_scheduler.py

# Terminal 4 - Backend
cd /app/backend && python server.py

# Build Frontend (one-time)
cd /app/frontend && yarn build

# Copy to public folder
cp -r /app/frontend/build/* /path/to/public/folder/
```

---

## Troubleshooting

### CORS Errors
If you see CORS errors in browser console:
1. Check `/app/backend/.env` has correct `CORS_ORIGINS`
2. Restart backend server
3. Clear browser cache

### Backend Connection Refused
1. Verify backend is running: `curl http://localhost:9000/api/email-providers`
2. Check firewall: `sudo ufw allow 9000`
3. Check `.env` file has correct configuration

### Redis Connection Error
1. Verify Redis is running: `redis-cli ping`
2. Check `REDIS_URL` in `.env` file
3. Restart RQ workers

### Frontend API Calls Failing
1. Check `REACT_APP_BACKEND_URL` in frontend `.env`
2. Rebuild frontend: `yarn build`
3. Clear browser cache

---

## Security Checklist for Production

- [ ] Change `JWT_SECRET_KEY` to a secure random string
- [ ] Use specific CORS origins (not "*")
- [ ] Enable HTTPS (use Let's Encrypt for SSL certificates)
- [ ] Set strong MongoDB authentication
- [ ] Restrict Redis to localhost only
- [ ] Use environment-specific API keys
- [ ] Enable rate limiting on API endpoints
- [ ] Set up proper firewall rules
- [ ] Regular backups of MongoDB database
- [ ] Monitor logs for suspicious activity

---

## Support & Issues

If you encounter issues:
1. Check all services are running: `sudo supervisorctl status`
2. Review logs in `/var/log/supervisor/`
3. Verify environment variables are set correctly
4. Test each component individually

---

**Last Updated:** October 17, 2025
**Version:** 1.0.0
