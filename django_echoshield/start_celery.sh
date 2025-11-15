#!/bin/bash
# Start Celery worker and beat scheduler

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Create logs directory
mkdir -p logs

echo -e "${BLUE}Starting Celery services...${NC}"

# Start Celery worker in background
celery -A echoshield worker --loglevel=info > logs/celery_worker.log 2>&1 &
WORKER_PID=$!

# Start Celery beat in background
celery -A echoshield beat --loglevel=info > logs/celery_beat.log 2>&1 &
BEAT_PID=$!

echo -e "${GREEN}✓ Celery worker started (PID: $WORKER_PID)${NC}"
echo -e "${GREEN}✓ Celery beat started (PID: $BEAT_PID)${NC}"
echo ""
echo -e "${BLUE}Logs:${NC}"
echo "  - Worker: logs/celery_worker.log"
echo "  - Beat: logs/celery_beat.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop...${NC}"

# Wait for interrupt
trap "echo ''; echo -e '${BLUE}Stopping Celery services...${NC}'; kill $WORKER_PID $BEAT_PID 2>/dev/null; echo -e '${GREEN}Services stopped${NC}'; exit" INT TERM
wait
