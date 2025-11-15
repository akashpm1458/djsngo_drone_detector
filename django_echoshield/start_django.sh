#!/bin/bash
# Start Django development server

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
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

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Warning: .env file not found${NC}"
    echo "Run ./setup.sh first"
fi

echo -e "${BLUE}Starting Django development server...${NC}"
echo -e "${GREEN}Server will be available at: http://localhost:8000${NC}"
echo -e "${BLUE}Press Ctrl+C to stop${NC}"
echo ""

python manage.py runserver 0.0.0.0:8000
