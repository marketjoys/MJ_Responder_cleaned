#!/bin/bash

################################################################################
# Automated Deployment Script for MJ_Responder Email Automation
# 
# This script will:
# 1. Clone repository from GitHub (branch: BOulookIMP)
# 2. Install Redis and configure it
# 3. Install Python and Node.js dependencies
# 4. Configure RQ workers
# 5. Start backend on port 9000
# 6. Build production-ready frontend
# 7. Handle all CORS configurations
#
# Usage: ./deploy_from_github.sh [target_directory]
# Example: ./deploy_from_github.sh /opt/email-automation
################################################################################

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
GITHUB_REPO="https://github.com/marketjoys/MJ_Responder_cleaned.git"
GITHUB_BRANCH="BOulookIMP"
DEFAULT_INSTALL_DIR="$HOME/email-automation"
BACKEND_PORT=9000
DOMAIN="marketautomailer.mj.publicvm.com"

# Get installation directory
INSTALL_DIR="${1:-$DEFAULT_INSTALL_DIR}"

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║   MJ Responder Email Automation - Automated Deployment    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

################################################################################
# Function: Print section header
################################################################################
print_section() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

################################################################################
# Function: Check if command exists
################################################################################
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

################################################################################
# Function: Install Redis
################################################################################
install_redis() {
    print_section "📦 Installing Redis"
    
    if command_exists redis-server; then
        echo -e "${GREEN}✅ Redis is already installed${NC}"
        redis-server --version
        return 0
    fi
    
    echo -e "${YELLOW}Installing Redis...${NC}"
    
    # Detect OS
    if [ -f /etc/debian_version ]; then
        # Debian/Ubuntu
        sudo apt-get update
        sudo apt-get install -y redis-server
    elif [ -f /etc/redhat-release ]; then
        # RHEL/CentOS
        sudo yum install -y redis
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command_exists brew; then
            brew install redis
        else
            echo -e "${RED}❌ Homebrew not found. Please install Redis manually.${NC}"
            exit 1
        fi
    else
        echo -e "${RED}❌ Unsupported OS. Please install Redis manually.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Redis installed successfully${NC}"
}

################################################################################
# Function: Start Redis
################################################################################
start_redis() {
    print_section "🚀 Starting Redis"
    
    # Check if Redis is already running
    if redis-cli ping >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Redis is already running${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}Starting Redis server...${NC}"
    
    # Try to start Redis as a service first
    if command_exists systemctl; then
        sudo systemctl start redis-server 2>/dev/null || sudo systemctl start redis 2>/dev/null || redis-server --daemonize yes
    else
        redis-server --daemonize yes
    fi
    
    sleep 2
    
    if redis-cli ping >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Redis started successfully${NC}"
    else
        echo -e "${RED}❌ Failed to start Redis${NC}"
        exit 1
    fi
}

################################################################################
# Function: Clone repository
################################################################################
clone_repository() {
    print_section "📥 Cloning Repository from GitHub"
    
    echo -e "Repository: ${YELLOW}$GITHUB_REPO${NC}"
    echo -e "Branch: ${YELLOW}$GITHUB_BRANCH${NC}"
    echo -e "Target Directory: ${YELLOW}$INSTALL_DIR${NC}\n"
    
    # Check if directory already exists
    if [ -d "$INSTALL_DIR" ]; then
        echo -e "${YELLOW}⚠️  Directory already exists: $INSTALL_DIR${NC}"
        read -p "Do you want to remove it and clone fresh? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$INSTALL_DIR"
        else
            echo -e "${YELLOW}Using existing directory...${NC}"
            cd "$INSTALL_DIR"
            git fetch origin
            git checkout "$GITHUB_BRANCH"
            git pull origin "$GITHUB_BRANCH"
            return 0
        fi
    fi
    
    # Clone repository
    git clone -b "$GITHUB_BRANCH" "$GITHUB_REPO" "$INSTALL_DIR"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Repository cloned successfully${NC}"
        cd "$INSTALL_DIR"
    else
        echo -e "${RED}❌ Failed to clone repository${NC}"
        exit 1
    fi
}

################################################################################
# Function: Auto-detect project structure
################################################################################
detect_structure() {
    print_section "🔍 Detecting Project Structure"
    
    cd "$INSTALL_DIR"
    
    # Find backend directory
    if [ -d "backend" ]; then
        BACKEND_DIR="$INSTALL_DIR/backend"
        echo -e "${GREEN}✅ Backend directory found: $BACKEND_DIR${NC}"
    else
        echo -e "${RED}❌ Backend directory not found${NC}"
        exit 1
    fi
    
    # Find frontend directory
    if [ -d "frontend" ]; then
        FRONTEND_DIR="$INSTALL_DIR/frontend"
        echo -e "${GREEN}✅ Frontend directory found: $FRONTEND_DIR${NC}"
    else
        echo -e "${YELLOW}⚠️  Frontend directory not found${NC}"
        FRONTEND_DIR=""
    fi
    
    echo -e "\n${BLUE}Project Structure:${NC}"
    echo -e "  Root: $INSTALL_DIR"
    echo -e "  Backend: $BACKEND_DIR"
    echo -e "  Frontend: $FRONTEND_DIR"
}

################################################################################
# Function: Install Python dependencies
################################################################################
install_python_dependencies() {
    print_section "🐍 Installing Python Dependencies"
    
    cd "$BACKEND_DIR"
    
    # Check if requirements.txt exists
    if [ ! -f "requirements.txt" ]; then
        echo -e "${RED}❌ requirements.txt not found${NC}"
        exit 1
    fi
    
    # Check Python version
    if ! command_exists python3; then
        echo -e "${RED}❌ Python 3 is not installed. Please install Python 3.8+${NC}"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    echo -e "Python version: ${GREEN}$PYTHON_VERSION${NC}\n"
    
    # Create virtual environment (optional but recommended)
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv || true
    
    # Activate virtual environment if it exists
    if [ -d "venv" ]; then
        source venv/bin/activate
        echo -e "${GREEN}✅ Virtual environment activated${NC}\n"
    fi
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    echo -e "${YELLOW}Installing Python packages...${NC}"
    pip install -r requirements.txt
    
    # Ensure Redis, RQ, and RQ-Scheduler are installed
    pip install redis rq rq-scheduler
    
    echo -e "${GREEN}✅ Python dependencies installed${NC}"
}

################################################################################
# Function: Configure environment variables
################################################################################
configure_environment() {
    print_section "⚙️  Configuring Environment Variables"
    
    cd "$BACKEND_DIR"
    
    # Check if .env exists
    if [ -f ".env" ]; then
        echo -e "${YELLOW}.env file already exists${NC}"
        read -p "Do you want to update CORS and port settings? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return 0
        fi
    else
        echo -e "${YELLOW}Creating .env file...${NC}"
        cat > .env << EOF
# Database
MONGO_URL="mongodb://localhost:27017"
DB_NAME="email_automation_db"

# Redis
REDIS_URL="redis://localhost:6379/0"

# CORS Origins - IMPORTANT
CORS_ORIGINS="http://$DOMAIN,http://localhost:3000,http://localhost:$BACKEND_PORT"

# API Keys (Update these with your actual keys)
GROQ_API_KEY="your-groq-api-key-here"
COHERE_API_KEY="your-cohere-api-key-here"

# Security
JWT_SECRET_KEY="$(openssl rand -hex 32)"
ENCRYPTION_KEY="$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"

# OAuth Configuration (Update with your credentials)
GOOGLE_CLIENT_ID="your-google-client-id"
GOOGLE_CLIENT_SECRET="your-google-client-secret"
GOOGLE_REDIRECT_URI="http://$DOMAIN/oauth/google/callback"

MICROSOFT_CLIENT_ID="your-microsoft-client-id"
MICROSOFT_CLIENT_SECRET="your-microsoft-client-secret"
MICROSOFT_TENANT_ID="common"
MICROSOFT_REDIRECT_URI="http://$DOMAIN/oauth/microsoft/callback"
EOF
    fi
    
    # Update CORS_ORIGINS if .env exists
    if grep -q "CORS_ORIGINS" .env; then
        sed -i.bak "s|CORS_ORIGINS=.*|CORS_ORIGINS=\"http://$DOMAIN,http://localhost:3000,http://localhost:$BACKEND_PORT\"|g" .env
        echo -e "${GREEN}✅ CORS_ORIGINS updated${NC}"
    fi
    
    echo -e "\n${YELLOW}⚠️  IMPORTANT: Please update the following in .env:${NC}"
    echo -e "  - GROQ_API_KEY"
    echo -e "  - COHERE_API_KEY"
    echo -e "  - OAuth credentials (if using OAuth)"
    echo -e "\n${BLUE}Edit with: nano $BACKEND_DIR/.env${NC}"
    
    read -p "Press Enter to continue after updating .env (or continue without updating)..."
}

################################################################################
# Function: Create RQ worker scripts
################################################################################
create_worker_scripts() {
    print_section "👷 Creating RQ Worker Scripts"
    
    cd "$BACKEND_DIR"
    
    # Check if start_worker.py exists
    if [ ! -f "start_worker.py" ]; then
        echo -e "${YELLOW}Creating start_worker.py...${NC}"
        cat > start_worker.py << 'EOF'
#!/usr/bin/env python3
"""
RQ Worker Startup Script
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from redis import Redis
from rq import Worker, Queue

# Redis connection
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
redis_conn = Redis.from_url(redis_url)

# Queue names
queues = ['email-processing', 'follow-up', 'background']

print(f"✅ RQ Worker starting - listening on queues: {queues}")
print(f"🕐 Scheduler support: ENABLED")

# Create worker
worker = Worker(queues, connection=redis_conn)

# Start worker
worker.work(with_scheduler=True)
EOF
        chmod +x start_worker.py
        echo -e "${GREEN}✅ start_worker.py created${NC}"
    else
        echo -e "${GREEN}✅ start_worker.py already exists${NC}"
    fi
    
    # Check if start_scheduler.py exists
    if [ ! -f "start_scheduler.py" ]; then
        echo -e "${YELLOW}Creating start_scheduler.py...${NC}"
        cat > start_scheduler.py << 'EOF'
#!/usr/bin/env python3
"""
RQ Scheduler Startup Script
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from redis import Redis
from rq_scheduler import Scheduler

# Redis connection
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
redis_conn = Redis.from_url(redis_url)

print("✅ RQ Scheduler starting...")

# Create scheduler
scheduler = Scheduler(connection=redis_conn, interval=60)

# Start scheduler
scheduler.run()
EOF
        chmod +x start_scheduler.py
        echo -e "${GREEN}✅ start_scheduler.py created${NC}"
    else
        echo -e "${GREEN}✅ start_scheduler.py already exists${NC}"
    fi
}

################################################################################
# Function: Start backend services
################################################################################
start_backend() {
    print_section "🚀 Starting Backend Services"
    
    cd "$BACKEND_DIR"
    
    # Activate virtual environment if exists
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # Create logs directory
    mkdir -p logs
    
    # Kill existing processes
    pkill -f "start_worker.py" 2>/dev/null || true
    pkill -f "start_scheduler.py" 2>/dev/null || true
    pkill -f "uvicorn server:app.*$BACKEND_PORT" 2>/dev/null || true
    
    sleep 2
    
    # Start RQ Worker
    echo -e "${YELLOW}Starting RQ Worker...${NC}"
    nohup python start_worker.py > logs/rq_worker.log 2>&1 &
    RQ_WORKER_PID=$!
    echo -e "${GREEN}✅ RQ Worker started (PID: $RQ_WORKER_PID)${NC}"
    
    sleep 2
    
    # Start RQ Scheduler
    echo -e "${YELLOW}Starting RQ Scheduler...${NC}"
    nohup python start_scheduler.py > logs/rq_scheduler.log 2>&1 &
    RQ_SCHEDULER_PID=$!
    echo -e "${GREEN}✅ RQ Scheduler started (PID: $RQ_SCHEDULER_PID)${NC}"
    
    sleep 2
    
    # Start Backend on specified port
    echo -e "${YELLOW}Starting Backend on port $BACKEND_PORT...${NC}"
    nohup uvicorn server:app --host 0.0.0.0 --port $BACKEND_PORT > logs/backend.log 2>&1 &
    BACKEND_PID=$!
    echo -e "${GREEN}✅ Backend started (PID: $BACKEND_PID)${NC}"
    
    sleep 3
    
    # Verify services are running
    echo -e "\n${BLUE}Verifying services...${NC}"
    
    if pgrep -f "start_worker.py" > /dev/null; then
        echo -e "${GREEN}✅ RQ Worker is running${NC}"
    else
        echo -e "${RED}❌ RQ Worker failed to start${NC}"
    fi
    
    if pgrep -f "start_scheduler.py" > /dev/null; then
        echo -e "${GREEN}✅ RQ Scheduler is running${NC}"
    else
        echo -e "${RED}❌ RQ Scheduler failed to start${NC}"
    fi
    
    if lsof -i:$BACKEND_PORT > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend is running on port $BACKEND_PORT${NC}"
    else
        echo -e "${RED}❌ Backend failed to start on port $BACKEND_PORT${NC}"
    fi
    
    # Save PIDs for later management
    echo "$RQ_WORKER_PID" > logs/rq_worker.pid
    echo "$RQ_SCHEDULER_PID" > logs/rq_scheduler.pid
    echo "$BACKEND_PID" > logs/backend.pid
}

################################################################################
# Function: Install frontend dependencies
################################################################################
install_frontend_dependencies() {
    print_section "📦 Installing Frontend Dependencies"
    
    if [ -z "$FRONTEND_DIR" ]; then
        echo -e "${YELLOW}⚠️  No frontend directory found, skipping...${NC}"
        return 0
    fi
    
    cd "$FRONTEND_DIR"
    
    # Check if package.json exists
    if [ ! -f "package.json" ]; then
        echo -e "${RED}❌ package.json not found${NC}"
        return 1
    fi
    
    # Check if yarn is installed
    if ! command_exists yarn; then
        echo -e "${YELLOW}Yarn not found. Installing via npm...${NC}"
        npm install -g yarn
    fi
    
    echo -e "${YELLOW}Installing Node.js packages...${NC}"
    yarn install
    
    echo -e "${GREEN}✅ Frontend dependencies installed${NC}"
}

################################################################################
# Function: Configure frontend environment
################################################################################
configure_frontend_env() {
    print_section "⚙️  Configuring Frontend Environment"
    
    if [ -z "$FRONTEND_DIR" ]; then
        echo -e "${YELLOW}⚠️  No frontend directory found, skipping...${NC}"
        return 0
    fi
    
    cd "$FRONTEND_DIR"
    
    # Create .env.production
    echo -e "${YELLOW}Creating .env.production...${NC}"
    cat > .env.production << EOF
# Backend API URL
REACT_APP_BACKEND_URL=http://$DOMAIN:$BACKEND_PORT/api

# Alternative configurations:
# For local testing: http://localhost:$BACKEND_PORT/api
# With web server proxy: http://$DOMAIN/api
EOF
    
    echo -e "${GREEN}✅ Frontend environment configured${NC}"
    echo -e "${BLUE}Backend URL set to: http://$DOMAIN:$BACKEND_PORT/api${NC}"
}

################################################################################
# Function: Build frontend
################################################################################
build_frontend() {
    print_section "🏗️  Building Production Frontend"
    
    if [ -z "$FRONTEND_DIR" ]; then
        echo -e "${YELLOW}⚠️  No frontend directory found, skipping...${NC}"
        return 0
    fi
    
    cd "$FRONTEND_DIR"
    
    # Clean previous build
    rm -rf build
    
    echo -e "${YELLOW}Creating production build...${NC}"
    yarn build
    
    if [ $? -eq 0 ]; then
        BUILD_SIZE=$(du -sh build 2>/dev/null | cut -f1)
        echo -e "${GREEN}✅ Frontend build completed successfully${NC}"
        echo -e "${BLUE}Build size: $BUILD_SIZE${NC}"
        echo -e "${BLUE}Build location: $FRONTEND_DIR/build${NC}"
    else
        echo -e "${RED}❌ Frontend build failed${NC}"
        return 1
    fi
}

################################################################################
# Function: Create deployment package
################################################################################
create_deployment_package() {
    print_section "📦 Creating Deployment Package"
    
    if [ -z "$FRONTEND_DIR" ] || [ ! -d "$FRONTEND_DIR/build" ]; then
        echo -e "${YELLOW}⚠️  No frontend build found, skipping...${NC}"
        return 0
    fi
    
    cd "$INSTALL_DIR"
    
    # Create deployment directory
    DEPLOY_DIR="$INSTALL_DIR/public_html_ready"
    rm -rf "$DEPLOY_DIR"
    mkdir -p "$DEPLOY_DIR"
    
    # Copy build files
    cp -r "$FRONTEND_DIR/build/"* "$DEPLOY_DIR/"
    
    # Create deployment info file
    cat > "$DEPLOY_DIR/DEPLOYMENT_INFO.txt" << EOF
MJ Responder Email Automation - Deployment Package
===================================================

Generated: $(date)
Backend URL: http://$DOMAIN:$BACKEND_PORT/api

DEPLOYMENT INSTRUCTIONS:
========================

1. Upload all files in this folder to your web server's public directory
   Example: /var/www/html/ or /usr/share/nginx/html/

2. Ensure backend is running on port $BACKEND_PORT

3. Configure web server (Nginx/Apache) to:
   - Serve static files from this directory
   - Proxy /api requests to http://localhost:$BACKEND_PORT/api
   - Support React Router (fallback to index.html)

4. Verify CORS settings in backend .env file include your domain

See web server configuration examples in:
$INSTALL_DIR/nginx.conf.example
$INSTALL_DIR/apache.conf.example
EOF
    
    echo -e "${GREEN}✅ Deployment package created${NC}"
    echo -e "${BLUE}Location: $DEPLOY_DIR${NC}"
    echo -e "\n${YELLOW}To deploy, copy all files from:${NC}"
    echo -e "${BLUE}$DEPLOY_DIR${NC}"
    echo -e "${YELLOW}to your web server's public folder${NC}"
}

################################################################################
# Function: Create web server configs
################################################################################
create_webserver_configs() {
    print_section "🌐 Creating Web Server Configuration Files"
    
    cd "$INSTALL_DIR"
    
    # Create Nginx configuration
    cat > nginx.conf.example << 'NGINX_EOF'
# Nginx Configuration
server {
    listen 80;
    server_name DOMAIN_PLACEHOLDER;
    
    client_max_body_size 50M;
    
    # Frontend
    location / {
        root /var/www/html/DEPLOY_DIR_NAME;
        index index.html;
        try_files $uri $uri/ /index.html;
    }
    
    # Backend API Proxy
    location /api/ {
        proxy_pass http://localhost:BACKEND_PORT_PLACEHOLDER/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # CORS
        add_header 'Access-Control-Allow-Origin' 'http://DOMAIN_PLACEHOLDER' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, PATCH, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization' always;
        add_header 'Access-Control-Allow-Credentials' 'true' always;
    }
    
    # OAuth
    location /oauth/ {
        proxy_pass http://localhost:BACKEND_PORT_PLACEHOLDER/oauth/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
NGINX_EOF
    
    sed -i "s|DOMAIN_PLACEHOLDER|$DOMAIN|g" nginx.conf.example
    sed -i "s|BACKEND_PORT_PLACEHOLDER|$BACKEND_PORT|g" nginx.conf.example
    sed -i "s|DEPLOY_DIR_NAME|$(basename "$DEPLOY_DIR" 2>/dev/null || echo "email-automation")|g" nginx.conf.example
    
    # Create Apache configuration
    cat > apache.conf.example << 'APACHE_EOF'
# Apache Configuration
<VirtualHost *:80>
    ServerName DOMAIN_PLACEHOLDER
    
    DocumentRoot /var/www/html/DEPLOY_DIR_NAME
    
    <Directory /var/www/html/DEPLOY_DIR_NAME>
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted
        
        RewriteEngine On
        RewriteBase /
        RewriteRule ^index\.html$ - [L]
        RewriteCond %{REQUEST_FILENAME} !-f
        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteCond %{REQUEST_URI} !^/api/
        RewriteCond %{REQUEST_URI} !^/oauth/
        RewriteRule . /index.html [L]
    </Directory>
    
    ProxyPreserveHost On
    ProxyRequests Off
    
    <Location /api>
        ProxyPass http://localhost:BACKEND_PORT_PLACEHOLDER/api
        ProxyPassReverse http://localhost:BACKEND_PORT_PLACEHOLDER/api
        
        Header always set Access-Control-Allow-Origin "http://DOMAIN_PLACEHOLDER"
        Header always set Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS"
        Header always set Access-Control-Allow-Headers "Content-Type, Authorization"
        Header always set Access-Control-Allow-Credentials "true"
    </Location>
    
    <Location /oauth>
        ProxyPass http://localhost:BACKEND_PORT_PLACEHOLDER/oauth
        ProxyPassReverse http://localhost:BACKEND_PORT_PLACEHOLDER/oauth
    </Location>
</VirtualHost>
APACHE_EOF
    
    sed -i "s|DOMAIN_PLACEHOLDER|$DOMAIN|g" apache.conf.example
    sed -i "s|BACKEND_PORT_PLACEHOLDER|$BACKEND_PORT|g" apache.conf.example
    sed -i "s|DEPLOY_DIR_NAME|$(basename "$DEPLOY_DIR" 2>/dev/null || echo "email-automation")|g" apache.conf.example
    
    echo -e "${GREEN}✅ Web server configurations created${NC}"
    echo -e "${BLUE}Nginx: $INSTALL_DIR/nginx.conf.example${NC}"
    echo -e "${BLUE}Apache: $INSTALL_DIR/apache.conf.example${NC}"
}

################################################################################
# Function: Create management scripts
################################################################################
create_management_scripts() {
    print_section "🛠️  Creating Management Scripts"
    
    cd "$INSTALL_DIR"
    
    # Create start script
    cat > start_services.sh << EOF
#!/bin/bash
# Start all services

cd "$BACKEND_DIR"

# Activate venv if exists
[ -d "venv" ] && source venv/bin/activate

# Start Redis if not running
redis-cli ping >/dev/null 2>&1 || redis-server --daemonize yes

# Start services
nohup python start_worker.py > logs/rq_worker.log 2>&1 &
nohup python start_scheduler.py > logs/rq_scheduler.log 2>&1 &
nohup uvicorn server:app --host 0.0.0.0 --port $BACKEND_PORT > logs/backend.log 2>&1 &

echo "✅ Services started"
echo "Backend: http://localhost:$BACKEND_PORT"
EOF
    
    # Create stop script
    cat > stop_services.sh << EOF
#!/bin/bash
# Stop all services

pkill -f "start_worker.py"
pkill -f "start_scheduler.py"
pkill -f "uvicorn server:app.*$BACKEND_PORT"

echo "✅ Services stopped"
EOF
    
    # Create status script
    cat > check_status.sh << EOF
#!/bin/bash
# Check services status

echo "Services Status:"
echo "================"
echo -n "Redis: "
redis-cli ping 2>/dev/null || echo "NOT RUNNING"

echo -n "RQ Worker: "
pgrep -f "start_worker.py" >/dev/null && echo "RUNNING" || echo "NOT RUNNING"

echo -n "RQ Scheduler: "
pgrep -f "start_scheduler.py" >/dev/null && echo "RUNNING" || echo "NOT RUNNING"

echo -n "Backend: "
lsof -i:$BACKEND_PORT >/dev/null 2>&1 && echo "RUNNING on port $BACKEND_PORT" || echo "NOT RUNNING"
EOF
    
    chmod +x start_services.sh stop_services.sh check_status.sh
    
    echo -e "${GREEN}✅ Management scripts created${NC}"
    echo -e "${BLUE}Start: ./start_services.sh${NC}"
    echo -e "${BLUE}Stop: ./stop_services.sh${NC}"
    echo -e "${BLUE}Status: ./check_status.sh${NC}"
}

################################################################################
# Function: Print completion summary
################################################################################
print_summary() {
    echo -e "\n${GREEN}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║            🎉 DEPLOYMENT COMPLETED SUCCESSFULLY            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    echo -e "${BLUE}📂 Installation Directory:${NC} $INSTALL_DIR"
    echo -e "${BLUE}🔧 Backend Directory:${NC} $BACKEND_DIR"
    [ -n "$FRONTEND_DIR" ] && echo -e "${BLUE}🎨 Frontend Directory:${NC} $FRONTEND_DIR"
    echo ""
    
    echo -e "${BLUE}🌐 Services:${NC}"
    echo -e "   Backend API: ${GREEN}http://localhost:$BACKEND_PORT/api${NC}"
    [ -d "$DEPLOY_DIR" ] && echo -e "   Frontend Build: ${GREEN}$DEPLOY_DIR${NC}"
    echo ""
    
    echo -e "${BLUE}📋 Management Commands:${NC}"
    echo -e "   Start Services:  ${YELLOW}$INSTALL_DIR/start_services.sh${NC}"
    echo -e "   Stop Services:   ${YELLOW}$INSTALL_DIR/stop_services.sh${NC}"
    echo -e "   Check Status:    ${YELLOW}$INSTALL_DIR/check_status.sh${NC}"
    echo ""
    
    echo -e "${BLUE}📦 Deployment Package:${NC}"
    if [ -d "$DEPLOY_DIR" ]; then
        echo -e "   Location: ${GREEN}$DEPLOY_DIR${NC}"
        echo -e "   ${YELLOW}Copy all files from above directory to your web server's public folder${NC}"
    fi
    echo ""
    
    echo -e "${BLUE}🔧 Web Server Configs:${NC}"
    echo -e "   Nginx:  ${YELLOW}$INSTALL_DIR/nginx.conf.example${NC}"
    echo -e "   Apache: ${YELLOW}$INSTALL_DIR/apache.conf.example${NC}"
    echo ""
    
    echo -e "${BLUE}📝 Logs:${NC}"
    echo -e "   Backend:      ${YELLOW}$BACKEND_DIR/logs/backend.log${NC}"
    echo -e "   RQ Worker:    ${YELLOW}$BACKEND_DIR/logs/rq_worker.log${NC}"
    echo -e "   RQ Scheduler: ${YELLOW}$BACKEND_DIR/logs/rq_scheduler.log${NC}"
    echo ""
    
    echo -e "${YELLOW}⚠️  NEXT STEPS:${NC}"
    echo -e "   1. Update API keys in: ${BLUE}$BACKEND_DIR/.env${NC}"
    echo -e "   2. Deploy frontend build to web server public folder"
    echo -e "   3. Configure web server (Nginx/Apache) using provided examples"
    echo -e "   4. Ensure MongoDB is running"
    echo -e "   5. Test the application at: ${GREEN}http://$DOMAIN${NC}"
    echo ""
}

################################################################################
# Main execution
################################################################################
main() {
    # Check prerequisites
    if ! command_exists git; then
        echo -e "${RED}❌ Git is not installed. Please install git first.${NC}"
        exit 1
    fi
    
    if ! command_exists python3; then
        echo -e "${RED}❌ Python 3 is not installed. Please install Python 3.8+${NC}"
        exit 1
    fi
    
    # Run deployment steps
    install_redis
    start_redis
    clone_repository
    detect_structure
    install_python_dependencies
    configure_environment
    create_worker_scripts
    start_backend
    
    # Frontend steps (if frontend exists)
    if [ -n "$FRONTEND_DIR" ]; then
        install_frontend_dependencies
        configure_frontend_env
        build_frontend
        create_deployment_package
    fi
    
    create_webserver_configs
    create_management_scripts
    print_summary
}

# Run main function
main "$@"
