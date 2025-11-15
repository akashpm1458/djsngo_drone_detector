#!/bin/bash
# Start ngrok tunnel for EchoShield

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting ngrok tunnel...${NC}"

# Check if ngrok is installed
if ! command -v ngrok >/dev/null 2>&1; then
    echo -e "${RED}Error: ngrok is not installed${NC}"
    echo "Run ./setup_ngrok.sh first"
    exit 1
fi

# Check if Django is running on port 8000
if ! nc -z localhost 8000 2>/dev/null; then
    echo -e "${YELLOW}Warning: Django server doesn't appear to be running on port 8000${NC}"
    echo "Start Django server first: ./start_django.sh"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}Starting ngrok tunnel to http://localhost:8000${NC}"
echo -e "${BLUE}Press Ctrl+C to stop ngrok${NC}"
echo ""

# Start ngrok
ngrok http 8000

