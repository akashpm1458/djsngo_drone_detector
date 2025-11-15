#!/bin/bash
# ngrok Setup Script for EchoShield
# This script helps set up ngrok for remote access

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}ngrok Setup for EchoShield${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if ngrok is installed
if ! command_exists ngrok; then
    echo -e "${YELLOW}ngrok is not installed.${NC}"
    echo ""
    echo "Please install ngrok:"
    echo "1. Download from: https://ngrok.com/download"
    echo "2. Extract and add to your PATH"
    echo "3. Or install via package manager:"
    echo "   - macOS: brew install ngrok/ngrok/ngrok"
    echo "   - Linux: Download from https://ngrok.com/download"
    echo "   - Windows: Download from https://ngrok.com/download"
    echo ""
    read -p "Press Enter after installing ngrok, or Ctrl+C to exit..."
fi

# Check if ngrok is authenticated
if ! ngrok config check >/dev/null 2>&1; then
    echo -e "${YELLOW}ngrok is not authenticated.${NC}"
    echo ""
    echo "To authenticate ngrok:"
    echo "1. Sign up for a free account at: https://dashboard.ngrok.com/signup"
    echo "2. Get your authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken"
    echo ""
    read -p "Enter your ngrok authtoken: " AUTHTOKEN
    
    if [ -z "$AUTHTOKEN" ]; then
        echo -e "${RED}Error: Authtoken cannot be empty${NC}"
        exit 1
    fi
    
    ngrok config add-authtoken "$AUTHTOKEN"
    echo -e "${GREEN}✓ ngrok authenticated${NC}"
else
    echo -e "${GREEN}✓ ngrok is already authenticated${NC}"
fi

echo ""

# Update .env file with ngrok URL placeholder
if [ -f ".env" ]; then
    echo -e "${BLUE}Updating .env file...${NC}"
    
    # Check if ALLOWED_HOSTS already has ngrok placeholder
    if ! grep -q "ngrok-free.app" .env; then
        # Add ngrok domain placeholder
        sed -i.bak 's/ALLOWED_HOSTS=.*/ALLOWED_HOSTS=localhost,127.0.0.1,*.ngrok-free.app/' .env
        echo -e "${GREEN}✓ Updated ALLOWED_HOSTS in .env${NC}"
        echo -e "${YELLOW}⚠ You'll need to update .env with your actual ngrok URL after starting ngrok${NC}"
    else
        echo -e "${GREEN}✓ .env already configured for ngrok${NC}"
    fi
else
    echo -e "${YELLOW}⚠ .env file not found. Run setup.sh first.${NC}"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}ngrok Setup Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "To start ngrok tunnel:"
echo "  1. Make sure Django server is running on port 8000"
echo "  2. Run: ngrok http 8000"
echo "  3. Copy the HTTPS URL (e.g., https://abc123.ngrok-free.app)"
echo "  4. Update .env file: ALLOWED_HOSTS=localhost,127.0.0.1,abc123.ngrok-free.app"
echo "  5. Restart Django server"
echo ""
echo "Or use the start script:"
echo "  ./start_ngrok.sh"
echo ""

