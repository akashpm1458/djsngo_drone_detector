#!/bin/bash
# Development startup script for EchoShield Django

echo "Starting EchoShield Development Environment..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${BLUE}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
echo -e "${BLUE}Installing dependencies...${NC}"
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${BLUE}Creating .env file from example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}.env file created. Please review and update as needed.${NC}"
fi

# Run setup command
echo -e "${BLUE}Running setup...${NC}"
python manage.py setup_echoshield

# Start services in separate terminal windows or tmux panes
echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "To start the services manually, run:"
echo ""
echo "Terminal 1 - Django server:"
echo "  python manage.py runserver 0.0.0.0:8000"
echo ""
echo "Terminal 2 - Celery worker:"
echo "  celery -A echoshield worker -l info"
echo ""
echo "Terminal 3 - Celery beat:"
echo "  celery -A echoshield beat -l info"
echo ""
echo "Or use the provided scripts:"
echo "  ./start_django.sh"
echo "  ./start_celery.sh"
echo ""
