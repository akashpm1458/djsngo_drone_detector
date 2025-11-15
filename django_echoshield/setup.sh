#!/bin/bash
# EchoShield Django Setup Script
# This script automates the complete setup process for EchoShield

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}EchoShield Django Setup Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

# Check Python
if ! command_exists python3 && ! command_exists python; then
    echo -e "${RED}Error: Python 3 is not installed. Please install Python 3.9 or higher.${NC}"
    exit 1
fi

PYTHON_CMD="python3"
if ! command_exists python3; then
    PYTHON_CMD="python"
fi

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓ Python found: $PYTHON_VERSION${NC}"

# Check pip
if ! command_exists pip3 && ! command_exists pip; then
    echo -e "${RED}Error: pip is not installed. Please install pip.${NC}"
    exit 1
fi

PIP_CMD="pip3"
if ! command_exists pip3; then
    PIP_CMD="pip"
fi

echo -e "${GREEN}✓ pip found${NC}"

# Check Redis (optional but recommended)
if command_exists redis-cli; then
    if redis-cli ping >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Redis is running${NC}"
    else
        echo -e "${YELLOW}⚠ Redis is installed but not running. Start it with: redis-server${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Redis not found. Celery will not work without Redis.${NC}"
    echo -e "${YELLOW}  Install Redis: https://redis.io/download${NC}"
fi

echo ""

# Step 1: Create virtual environment
echo -e "${BLUE}Step 1: Setting up virtual environment...${NC}"
if [ ! -d "venv" ]; then
    echo -e "${BLUE}Creating virtual environment...${NC}"
    $PYTHON_CMD -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "${BLUE}Upgrading pip...${NC}"
$PIP_CMD install --upgrade pip --quiet

echo ""

# Step 2: Install dependencies
echo -e "${BLUE}Step 2: Installing dependencies...${NC}"
$PIP_CMD install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Step 3: Create .env file
echo -e "${BLUE}Step 3: Setting up environment variables...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${BLUE}Creating .env file...${NC}"
    cat > .env << EOF
# Django Settings
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (SQLite by default)
DATABASE_PATH=db.sqlite3

# Celery (Redis)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# EchoShield Configuration
INGEST_URL=http://localhost:8000/api/v0/ingest/wire
NODE_RETENTION_SECONDS=60
GCC_PHAT_MAX_RADIUS_M=100.0
SPEED_OF_SOUND=343.0
AGGREGATION_WINDOW_NS=10000000000
MIN_TRACK_CONTRIBUTORS=2
EOF
    echo -e "${GREEN}✓ .env file created${NC}"
    echo -e "${YELLOW}⚠ Please review .env file and update ALLOWED_HOSTS if using ngrok${NC}"
else
    echo -e "${GREEN}✓ .env file already exists${NC}"
fi
echo ""

# Step 4: Run database migrations
echo -e "${BLUE}Step 4: Setting up database...${NC}"
python manage.py migrate
echo -e "${GREEN}✓ Database migrations completed${NC}"
echo ""

# Step 5: Initialize detection configurations
echo -e "${BLUE}Step 5: Initializing detection configurations...${NC}"
if python manage.py init_detection_configs 2>/dev/null; then
    echo -e "${GREEN}✓ Detection configurations initialized${NC}"
else
    echo -e "${YELLOW}⚠ Detection configurations may already exist${NC}"
fi
echo ""

# Step 6: Create superuser (optional)
echo -e "${BLUE}Step 6: Creating admin superuser...${NC}"
echo -e "${YELLOW}You can skip this step by pressing Ctrl+C${NC}"
read -p "Create superuser? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python manage.py createsuperuser || echo -e "${YELLOW}Superuser creation skipped or failed${NC}"
else
    echo -e "${BLUE}Skipping superuser creation${NC}"
fi
echo ""

# Step 7: Collect static files
echo -e "${BLUE}Step 7: Collecting static files...${NC}"
python manage.py collectstatic --noinput
echo -e "${GREEN}✓ Static files collected${NC}"
echo ""

# Step 8: Create logs directory
echo -e "${BLUE}Step 8: Creating logs directory...${NC}"
mkdir -p logs
echo -e "${GREEN}✓ Logs directory created${NC}"
echo ""

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo ""
echo "1. Start Redis (if not running):"
echo "   redis-server"
echo ""
echo "2. Start Django server:"
echo "   ./start_django.sh"
echo "   or"
echo "   source venv/bin/activate"
echo "   python manage.py runserver 0.0.0.0:8000"
echo ""
echo "3. (Optional) Start Celery worker and beat:"
echo "   ./start_celery.sh"
echo ""
echo "4. (Optional) Set up ngrok for remote access:"
echo "   ./setup_ngrok.sh"
echo ""
echo -e "${BLUE}Access the application:${NC}"
echo "  - Edge Detection UI: http://localhost:8000/edge_client/detect"
echo "  - Dashboard: http://localhost:8000/monitoring/dashboard"
echo "  - Admin: http://localhost:8000/admin/"
echo ""
echo -e "${GREEN}Happy detecting!${NC}"

