# EchoShield Setup Scripts

This directory contains bash scripts to automate the setup and running of the EchoShield Django application.

## Quick Start

1. **Initial Setup** (run once):
   ```bash
   ./setup.sh
   ```

2. **Start Services**:
   ```bash
   ./start_all.sh
   ```

That's it! The application will be available at http://localhost:8000

## Available Scripts

### Setup Scripts

#### `setup.sh`
Complete initial setup script. This script:
- Checks prerequisites (Python, pip, Redis)
- Creates virtual environment
- Installs all dependencies
- Creates `.env` file with secure defaults
- Runs database migrations
- Initializes detection configurations
- Optionally creates admin superuser
- Collects static files

**Usage:**
```bash
./setup.sh
```

#### `setup_ngrok.sh`
Sets up ngrok for remote access. This script:
- Checks if ngrok is installed
- Authenticates ngrok with your authtoken
- Updates `.env` file for ngrok domains

**Usage:**
```bash
./setup_ngrok.sh
```

**Prerequisites:**
- ngrok installed (download from https://ngrok.com/download)
- ngrok account and authtoken

### Service Start Scripts

#### `start_django.sh`
Starts the Django development server on port 8000.

**Usage:**
```bash
./start_django.sh
```

**Access:**
- Edge Detection UI: http://localhost:8000/edge_client/detect
- Dashboard: http://localhost:8000/monitoring/dashboard
- Admin: http://localhost:8000/admin/

#### `start_celery.sh`
Starts Celery worker and beat scheduler for background tasks.

**Usage:**
```bash
./start_celery.sh
```

**Prerequisites:**
- Redis must be running

#### `start_all.sh`
Starts all services (Django, Celery worker, Celery beat) in a single script.

**Usage:**
```bash
./start_all.sh
```

This script:
- Starts Django server in background
- Starts Celery worker in background
- Starts Celery beat in background
- Logs output to `logs/` directory
- Handles cleanup on Ctrl+C

#### `start_ngrok.sh`
Starts ngrok tunnel to expose Django server.

**Usage:**
```bash
./start_ngrok.sh
```

**Prerequisites:**
- ngrok installed and authenticated
- Django server running on port 8000

### Utility Scripts

#### `check_setup.sh`
Checks the current setup status and reports:
- Python and pip installation
- Virtual environment status
- Redis status
- ngrok status
- Project files
- Installed packages
- Running services

**Usage:**
```bash
./check_setup.sh
```

## Script Workflow

### First Time Setup

```bash
# 1. Run initial setup
./setup.sh

# 2. (Optional) Set up ngrok for remote access
./setup_ngrok.sh

# 3. Start all services
./start_all.sh
```

### Daily Development

```bash
# Option 1: Start all services together
./start_all.sh

# Option 2: Start services separately (in different terminals)
./start_django.sh    # Terminal 1
./start_celery.sh    # Terminal 2
```

### With ngrok (Remote Access)

```bash
# Terminal 1: Start Django
./start_django.sh

# Terminal 2: Start ngrok
./start_ngrok.sh

# Terminal 3: (Optional) Start Celery
./start_celery.sh
```

## Making Scripts Executable

If scripts are not executable, make them executable:

```bash
chmod +x setup.sh
chmod +x setup_ngrok.sh
chmod +x start_django.sh
chmod +x start_celery.sh
chmod +x start_all.sh
chmod +x start_ngrok.sh
chmod +x check_setup.sh
```

Or make all scripts executable at once:

```bash
chmod +x *.sh
```

## Windows Users

These scripts are designed for Linux/macOS/Git Bash. On Windows:

1. **Use Git Bash** (recommended):
   - Install Git for Windows (includes Git Bash)
   - Open Git Bash
   - Navigate to project directory
   - Run scripts as shown above

2. **Use WSL** (Windows Subsystem for Linux):
   - Install WSL
   - Open WSL terminal
   - Run scripts as shown above

3. **Use PowerShell** (alternative):
   - PowerShell equivalents can be created if needed
   - Or use the scripts via Git Bash

## Troubleshooting

### Script Permission Denied

```bash
chmod +x script_name.sh
```

### Virtual Environment Not Found

Run setup first:
```bash
./setup.sh
```

### Redis Not Running

Start Redis:
```bash
# Linux
sudo systemctl start redis
# or
redis-server

# macOS
brew services start redis
# or
redis-server

# Windows (Git Bash)
# Download and run redis-server.exe
```

### Port 8000 Already in Use

Either:
1. Stop the process using port 8000
2. Or change the port in `start_django.sh`:
   ```bash
   python manage.py runserver 0.0.0.0:8001
   ```

### ngrok Not Found

1. Install ngrok: https://ngrok.com/download
2. Add to PATH or use full path
3. Run `./setup_ngrok.sh` to authenticate

## Log Files

When using `start_all.sh` or `start_celery.sh`, logs are written to:
- `logs/django.log` - Django server logs
- `logs/celery_worker.log` - Celery worker logs
- `logs/celery_beat.log` - Celery beat logs

## Environment Variables

The `.env` file is created by `setup.sh`. Key variables:

- `SECRET_KEY` - Django secret key (auto-generated)
- `DEBUG` - Debug mode (True for development)
- `ALLOWED_HOSTS` - Allowed hostnames
- `CELERY_BROKER_URL` - Redis URL for Celery
- `DATABASE_PATH` - SQLite database path

Update `.env` manually or re-run `setup.sh` (it won't overwrite existing `.env`).

## Next Steps

After setup:
1. Access the application at http://localhost:8000
2. Create detection configurations via Django admin
3. Test edge detection with audio uploads
4. View detections on the dashboard
5. Set up ngrok for remote access if needed

For more details, see `SETUP_GUIDE.md`.

