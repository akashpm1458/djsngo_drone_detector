#!/bin/bash
# Check EchoShield setup status

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}EchoShield Setup Check${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if file/directory exists
check_exists() {
    if [ -e "$1" ]; then
        echo -e "${GREEN}✓${NC} $2"
        return 0
    else
        echo -e "${RED}✗${NC} $2"
        return 1
    fi
}

# Check Python
echo -e "${BLUE}Checking Python...${NC}"
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo -e "${GREEN}✓${NC} Python: $PYTHON_VERSION"
elif command_exists python; then
    PYTHON_VERSION=$(python --version 2>&1)
    echo -e "${GREEN}✓${NC} Python: $PYTHON_VERSION"
else
    echo -e "${RED}✗${NC} Python not found"
fi

# Check pip
echo -e "${BLUE}Checking pip...${NC}"
if command_exists pip3 || command_exists pip; then
    echo -e "${GREEN}✓${NC} pip installed"
else
    echo -e "${RED}✗${NC} pip not found"
fi

# Check virtual environment
echo -e "${BLUE}Checking virtual environment...${NC}"
check_exists "venv" "Virtual environment"

# Check Redis
echo -e "${BLUE}Checking Redis...${NC}"
if command_exists redis-cli; then
    if redis-cli ping >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Redis is running"
    else
        echo -e "${YELLOW}⚠${NC} Redis is installed but not running"
    fi
else
    echo -e "${YELLOW}⚠${NC} Redis not found (optional for Celery)"
fi

# Check ngrok
echo -e "${BLUE}Checking ngrok...${NC}"
if command_exists ngrok; then
    if ngrok config check >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} ngrok installed and authenticated"
    else
        echo -e "${YELLOW}⚠${NC} ngrok installed but not authenticated"
    fi
else
    echo -e "${YELLOW}⚠${NC} ngrok not found (optional for remote access)"
fi

# Check project files
echo -e "${BLUE}Checking project files...${NC}"
check_exists ".env" ".env file"
check_exists "requirements.txt" "requirements.txt"
check_exists "manage.py" "manage.py"
check_exists "db.sqlite3" "Database file" || echo -e "${YELLOW}⚠${NC} Database not created yet (run migrations)"

# Check if virtual environment is activated
if [ -n "$VIRTUAL_ENV" ]; then
    echo -e "${GREEN}✓${NC} Virtual environment is activated"
else
    echo -e "${YELLOW}⚠${NC} Virtual environment not activated"
fi

# Check installed packages
if [ -n "$VIRTUAL_ENV" ] || [ -d "venv" ]; then
    echo -e "${BLUE}Checking installed packages...${NC}"
    if [ -n "$VIRTUAL_ENV" ]; then
        source "$VIRTUAL_ENV/bin/activate" 2>/dev/null || true
    else
        source venv/bin/activate 2>/dev/null || true
    fi
    
    if python -c "import django" 2>/dev/null; then
        DJANGO_VERSION=$(python -c "import django; print(django.get_version())" 2>/dev/null)
        echo -e "${GREEN}✓${NC} Django $DJANGO_VERSION installed"
    else
        echo -e "${RED}✗${NC} Django not installed"
    fi
    
    if python -c "import celery" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Celery installed"
    else
        echo -e "${YELLOW}⚠${NC} Celery not installed"
    fi
    
    if python -c "import onnxruntime" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} onnxruntime installed (ML model support)"
    else
        echo -e "${YELLOW}⚠${NC} onnxruntime not installed (ML model will not work)"
    fi
fi

# Check running services
echo -e "${BLUE}Checking running services...${NC}"
if nc -z localhost 8000 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Django server is running on port 8000"
else
    echo -e "${YELLOW}⚠${NC} Django server is not running"
fi

if pgrep -f "celery.*worker" >/dev/null; then
    echo -e "${GREEN}✓${NC} Celery worker is running"
else
    echo -e "${YELLOW}⚠${NC} Celery worker is not running"
fi

if pgrep -f "celery.*beat" >/dev/null; then
    echo -e "${GREEN}✓${NC} Celery beat is running"
else
    echo -e "${YELLOW}⚠${NC} Celery beat is not running"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Setup check complete${NC}"
echo -e "${BLUE}========================================${NC}"

