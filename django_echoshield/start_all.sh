#!/bin/bash
# Start all EchoShield services
# This script starts Django, Celery worker, and Celery beat

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found${NC}"
    echo "Run ./setup.sh first"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if Redis is running
if command -v redis-cli >/dev/null 2>&1; then
    if ! redis-cli ping >/dev/null 2>&1; then
        echo -e "${YELLOW}Warning: Redis is not running${NC}"
        echo "Start Redis first: redis-server"
        read -p "Continue anyway? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Starting EchoShield Services${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Create logs directory
mkdir -p logs

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping services...${NC}"
    kill $DJANGO_PID $CELERY_WORKER_PID $CELERY_BEAT_PID 2>/dev/null || true
    echo -e "${GREEN}Services stopped${NC}"
    exit 0
}

trap cleanup INT TERM

# Start Django server
echo -e "${BLUE}Starting Django server...${NC}"
python manage.py runserver 0.0.0.0:8000 > logs/django.log 2>&1 &
DJANGO_PID=$!
echo -e "${GREEN}✓ Django server started (PID: $DJANGO_PID)${NC}"

# Wait a moment for Django to start
sleep 2

# Start Celery worker
echo -e "${BLUE}Starting Celery worker...${NC}"
celery -A echoshield worker --loglevel=info > logs/celery_worker.log 2>&1 &
CELERY_WORKER_PID=$!
echo -e "${GREEN}✓ Celery worker started (PID: $CELERY_WORKER_PID)${NC}"

# Start Celery beat
echo -e "${BLUE}Starting Celery beat...${NC}"
celery -A echoshield beat --loglevel=info > logs/celery_beat.log 2>&1 &
CELERY_BEAT_PID=$!
echo -e "${GREEN}✓ Celery beat started (PID: $CELERY_BEAT_PID)${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}All services started!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Services:${NC}"
echo "  - Django: http://localhost:8000 (PID: $DJANGO_PID)"
echo "  - Celery Worker (PID: $CELERY_WORKER_PID)"
echo "  - Celery Beat (PID: $CELERY_BEAT_PID)"
echo ""
echo -e "${BLUE}Access:${NC}"
echo "  - Edge Detection: http://localhost:8000/edge_client/detect"
echo "  - Dashboard: http://localhost:8000/monitoring/dashboard"
echo "  - Admin: http://localhost:8000/admin/"
echo ""
echo -e "${BLUE}Logs:${NC}"
echo "  - Django: logs/django.log"
echo "  - Celery Worker: logs/celery_worker.log"
echo "  - Celery Beat: logs/celery_beat.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for all background processes
wait

