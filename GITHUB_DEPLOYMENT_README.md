# 🚀 Automated GitHub Deployment Script

## One-Command Full Deployment from GitHub

This script automates the **complete deployment** of the MJ Responder Email Automation application directly from the GitHub repository.

---

## ✨ What This Script Does

1. ✅ **Clones repository** from GitHub (branch: BOulookIMP)
2. ✅ **Installs Redis** server automatically
3. ✅ **Installs all Python dependencies** (including RQ and workers)
4. ✅ **Creates and configures** RQ worker scripts
5. ✅ **Starts backend** on port 9000
6. ✅ **Installs frontend dependencies** (Node.js/Yarn)
7. ✅ **Builds production frontend** ready for deployment
8. ✅ **Handles all CORS** configurations automatically
9. ✅ **Creates web server configs** (Nginx and Apache)
10. ✅ **Provides management scripts** (start/stop/status)

---

## 🎯 Quick Start

### Basic Usage (Default Location)
```bash
wget https://raw.githubusercontent.com/yourusername/yourrepo/main/deploy_from_github.sh
chmod +x deploy_from_github.sh
./deploy_from_github.sh
```

This will install to: `~/email-automation`

### Custom Installation Directory
```bash
./deploy_from_github.sh /opt/email-automation
```

### Quick One-Liner
```bash
curl -fsSL https://raw.githubusercontent.com/yourusername/yourrepo/main/deploy_from_github.sh | bash
```

---

## 📋 Prerequisites

The script will check for these automatically:

**Required:**
- Git
- Python 3.8+
- Node.js 16+ (for frontend)
- MongoDB (must be running)

**Auto-Installed:**
- Redis (script installs it)
- Python packages (from requirements.txt)
- Node packages (from package.json)

---

## 🔧 What Gets Created

### Directory Structure
```
~/email-automation/               # Installation root
├── backend/                      # Backend application
│   ├── server.py                 # FastAPI server
│   ├── start_worker.py           # RQ worker script
│   ├── start_scheduler.py        # RQ scheduler script
│   ├── .env                      # Environment configuration
│   ├── venv/                     # Python virtual environment
│   └── logs/                     # Application logs
│       ├── backend.log
│       ├── rq_worker.log
│       └── rq_scheduler.log
│
├── frontend/                     # Frontend application
│   ├── src/                      # React source code
│   ├── build/                    # Production build
│   ├── .env.production           # Production config
│   └── package.json
│
├── public_html_ready/            # 📦 READY TO UPLOAD!
│   ├── index.html
│   ├── static/
│   └── DEPLOYMENT_INFO.txt       # Deployment instructions
│
├── nginx.conf.example            # Nginx configuration
├── apache.conf.example           # Apache configuration
├── start_services.sh             # Start all services
├── stop_services.sh              # Stop all services
└── check_status.sh               # Check services status
```

---

## 🚀 Running the Script

### Step-by-Step Execution

```bash
# 1. Download the script
curl -O https://path-to-script/deploy_from_github.sh
chmod +x deploy_from_github.sh

# 2. Run with default settings
./deploy_from_github.sh

# OR specify custom directory
./deploy_from_github.sh /opt/my-email-app

# 3. During execution, you'll be prompted to:
#    - Confirm directory removal (if exists)
#    - Update .env file with API keys
#    - Review configuration

# 4. After completion, update API keys
nano ~/email-automation/backend/.env

# 5. Services are auto-started!
```

---

## 📦 Frontend Deployment

After the script completes, you'll have a **production-ready build** in:
```
~/email-automation/public_html_ready/
```

### Deploy to Your Web Server

**Option 1: Direct Copy**
```bash
# Copy to Apache
sudo cp -r ~/email-automation/public_html_ready/* /var/www/html/

# Copy to Nginx
sudo cp -r ~/email-automation/public_html_ready/* /usr/share/nginx/html/
```

**Option 2: Using SCP (Remote Server)**
```bash
scp -r ~/email-automation/public_html_ready/* user@server:/var/www/html/
```

**Option 3: Using FTP/FileZilla**
Upload all files from `public_html_ready/` to your web server's public directory.

---

## 🌐 Web Server Configuration

### Configure Nginx

```bash
# Copy configuration
sudo cp ~/email-automation/nginx.conf.example /etc/nginx/sites-available/marketautomailer

# Edit if needed
sudo nano /etc/nginx/sites-available/marketautomailer

# Enable site
sudo ln -s /etc/nginx/sites-available/marketautomailer /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### Configure Apache

```bash
# Copy configuration
sudo cp ~/email-automation/apache.conf.example /etc/apache2/sites-available/marketautomailer.conf

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

## 🛠️ Managing Services

The script creates convenient management scripts:

### Start Services
```bash
cd ~/email-automation
./start_services.sh
```

### Stop Services
```bash
cd ~/email-automation
./stop_services.sh
```

### Check Status
```bash
cd ~/email-automation
./check_status.sh
```

### View Logs
```bash
# Backend logs
tail -f ~/email-automation/backend/logs/backend.log

# RQ Worker logs
tail -f ~/email-automation/backend/logs/rq_worker.log

# RQ Scheduler logs
tail -f ~/email-automation/backend/logs/rq_scheduler.log
```

---

## ⚙️ Configuration

### Backend Environment (.env)

After deployment, update these values in `~/email-automation/backend/.env`:

```bash
# Required API Keys
GROQ_API_KEY="your-actual-groq-api-key"
COHERE_API_KEY="your-actual-cohere-api-key"

# OAuth Credentials (if using OAuth)
GOOGLE_CLIENT_ID="your-google-client-id"
GOOGLE_CLIENT_SECRET="your-google-client-secret"

MICROSOFT_CLIENT_ID="your-microsoft-client-id"
MICROSOFT_CLIENT_SECRET="your-microsoft-client-secret"
```

### Frontend Environment

The script automatically creates `.env.production` with correct backend URL.

To change domain, edit:
```bash
nano ~/email-automation/frontend/.env.production
```

Then rebuild:
```bash
cd ~/email-automation/frontend
yarn build
```

---

## ✅ Verification

### Test Backend
```bash
# Check if backend is running
curl http://localhost:9000/api/email-providers

# Should return JSON response
```

### Test Services
```bash
# Redis
redis-cli ping
# Output: PONG

# Check all services
cd ~/email-automation
./check_status.sh
```

### Test Frontend
Navigate to: `http://marketautomailer.mj.publicvm.com`

---

## 🔧 Troubleshooting

### Script Fails to Clone Repository
```bash
# Ensure you have git access to the repository
git clone -b BOulookIMP https://github.com/marketjoys/MJ_Responder_cleaned.git test-clone

# If authentication required, set up SSH keys or personal access token
```

### Redis Installation Fails
```bash
# Manual installation (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install redis-server

# Manual installation (macOS)
brew install redis
```

### Backend Won't Start on Port 9000
```bash
# Check if port is in use
lsof -i:9000

# Kill process
kill -9 $(lsof -ti:9000)

# Try starting again
cd ~/email-automation/backend
uvicorn server:app --host 0.0.0.0 --port 9000
```

### CORS Errors in Browser
```bash
# Update CORS_ORIGINS in .env
nano ~/email-automation/backend/.env

# Add your domain
CORS_ORIGINS="http://marketautomailer.mj.publicvm.com,http://localhost:3000"

# Restart backend
cd ~/email-automation
./stop_services.sh
./start_services.sh
```

### Frontend Build Fails
```bash
# Clear node modules and rebuild
cd ~/email-automation/frontend
rm -rf node_modules build
yarn install
yarn build
```

---

## 🔄 Updating Deployment

To update from GitHub:

```bash
cd ~/email-automation

# Stop services
./stop_services.sh

# Pull latest changes
git fetch origin
git checkout BOulookIMP
git pull origin BOulookIMP

# Update dependencies
cd backend
pip install -r requirements.txt

cd ../frontend
yarn install

# Rebuild frontend
yarn build

# Copy new build
cp -r build/* ../public_html_ready/

# Restart services
cd ..
./start_services.sh
```

---

## 📊 Script Output

The script provides colored output:
- 🔵 **Blue**: Section headers
- 🟢 **Green**: Success messages
- 🟡 **Yellow**: Warnings/Info
- 🔴 **Red**: Errors

Example output:
```
╔════════════════════════════════════════════════════════════╗
║   MJ Responder Email Automation - Automated Deployment    ║
╚════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 Installing Redis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Redis is already installed
Redis server v=7.0.15

... (continues with all steps)
```

---

## 🔐 Security Notes

### Before Going Live:

1. **Update API Keys**: Replace placeholder keys in `.env`
2. **Strong JWT Secret**: Change `JWT_SECRET_KEY` to secure random string
3. **Specific CORS**: Don't use `"*"` in production
4. **HTTPS**: Set up SSL certificate (Let's Encrypt)
5. **MongoDB Auth**: Enable authentication on MongoDB
6. **Firewall**: Configure firewall rules properly

---

## 📞 Support

### Log Files
All logs are in: `~/email-automation/backend/logs/`

### Service Status
```bash
cd ~/email-automation
./check_status.sh
```

### Manual Service Management
```bash
# If automated scripts don't work, use these:

# Start Redis
redis-server --daemonize yes

# Start Backend
cd ~/email-automation/backend
source venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 9000 &

# Start RQ Worker
python start_worker.py &

# Start RQ Scheduler
python start_scheduler.py &
```

---

## 📝 Script Configuration

To customize the script behavior, edit these variables at the top:

```bash
GITHUB_REPO="https://github.com/marketjoys/MJ_Responder_cleaned.git"
GITHUB_BRANCH="BOulookIMP"
BACKEND_PORT=9000
DOMAIN="marketautomailer.mj.publicvm.com"
```

---

## ✨ Features

- ✅ Fully automated deployment
- ✅ Error handling and rollback
- ✅ Colored output for clarity
- ✅ Progress indicators
- ✅ Pre-flight checks
- ✅ Service verification
- ✅ Production-ready builds
- ✅ Complete CORS handling
- ✅ Management scripts included

---

**Last Updated:** October 17, 2025
**Version:** 1.0.0
**Repository:** https://github.com/marketjoys/MJ_Responder_cleaned (Branch: BOulookIMP)
