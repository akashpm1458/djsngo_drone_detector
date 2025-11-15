# EchoShield Setup Guide

This guide will help you set up the EchoShield Django application with ngrok for local development and testing.

## Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Redis (for Celery task queue)
- ngrok account (free tier is sufficient)
- Git (optional, for cloning the repository)

## Step 1: Install Python Dependencies

1. Navigate to the project directory:
```bash
cd django_echoshield
```

2. Create a virtual environment (recommended):
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

## Step 2: Set Up Environment Variables

1. Create a `.env` file in the `django_echoshield` directory:
```bash
# Copy from example if available, or create new
```

2. Add the following configuration to `.env`:
```env
# Django Settings
SECRET_KEY=your-secret-key-here-change-in-production
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
```

## Step 3: Set Up Database

1. Run database migrations:
```bash
python manage.py migrate
```

2. Initialize detection configurations:
```bash
python manage.py init_detection_configs
```

3. (Optional) Create a superuser for Django admin:
```bash
python manage.py createsuperuser
```

## Step 4: Install and Start Redis

### Windows:
1. Download Redis from: https://github.com/microsoftarchive/redis/releases
2. Extract and run `redis-server.exe`

### Linux:
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis
```

### Mac:
```bash
brew install redis
brew services start redis
```

Verify Redis is running:
```bash
redis-cli ping
# Should return: PONG
```

## Step 5: Start Django Development Server

1. Collect static files:
```bash
python manage.py collectstatic --noinput
```

2. Start the Django server:
```bash
python manage.py runserver 0.0.0.0:8000
```

The server should now be running at `http://localhost:8000`

## Step 6: Start Celery Worker (Optional, for background tasks)

Open a new terminal window and activate the virtual environment:

```bash
# Activate virtual environment
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

# Start Celery worker
celery -A echoshield worker --loglevel=info

# In another terminal, start Celery beat (for scheduled tasks)
celery -A echoshield beat --loglevel=info
```

## Step 7: Set Up ngrok

### Install ngrok

1. Download ngrok from: https://ngrok.com/download
2. Extract the executable to a location in your PATH, or add it to your PATH

### Authenticate ngrok

1. Sign up for a free ngrok account at: https://dashboard.ngrok.com/signup
2. Get your authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken
3. Authenticate:
```bash
ngrok config add-authtoken YOUR_AUTHTOKEN
```

### Start ngrok Tunnel

1. In a new terminal, start ngrok to tunnel to your Django server:
```bash
ngrok http 8000
```

2. ngrok will display a forwarding URL, for example:
```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8000
```

3. Copy the HTTPS URL (e.g., `https://abc123.ngrok-free.app`)

### Update Django Settings

1. Update your `.env` file to include the ngrok URL:
```env
ALLOWED_HOSTS=localhost,127.0.0.1,abc123.ngrok-free.app
```

2. Restart the Django server for changes to take effect

## Step 8: Access the Application

### Local Access:
- **Edge Detection UI**: http://localhost:8000/edge_client/detect
- **Monitoring Dashboard**: http://localhost:8000/monitoring/dashboard
- **Admin Interface**: http://localhost:8000/admin/
- **API Health Check**: http://localhost:8000/edge_client/health

### Remote Access (via ngrok):
- **Edge Detection UI**: https://abc123.ngrok-free.app/edge_client/detect
- **Monitoring Dashboard**: https://abc123.ngrok-free.app/monitoring/dashboard
- **Admin Interface**: https://abc123.ngrok-free.app/admin/

## Step 9: Configure Detection Methods

### Using Signal Processing (Default)

1. Access the Django admin: http://localhost:8000/admin/
2. Navigate to "Detection Configurations"
3. Create or edit a configuration:
   - Method: Select from Energy Likelihood, GCC-PHAT DOA, Harmonic Filter, or Combined
   - Configure parameters (fundamental frequency, harmonics, thresholds, etc.)
   - Set as active

### Using ML Model (ONNX)

1. Ensure the ONNX model file (`drone_33d_mlp.onnx`) is in the `django_echoshield` directory
2. Install onnxruntime (already in requirements.txt):
```bash
pip install onnxruntime
```

3. In Django admin, create a new Detection Configuration:
   - Method: Select "ML Model (ONNX)"
   - ML Model Path: `drone_33d_mlp.onnx` (or full path)
   - Use ML Model: Check this box
   - Set as active

4. Or use the edge client UI:
   - Go to http://localhost:8000/edge_client/detect
   - Select "ML Model (ONNX)" from the Detection Method dropdown
   - Upload or record audio

## Step 10: Test the System

1. **Test Edge Detection**:
   - Navigate to http://localhost:8000/edge_client/detect
   - Select detection method (Signal Processing or ML Model)
   - Upload an audio file or record live audio
   - View detection results

2. **View Dashboard**:
   - Navigate to http://localhost:8000/monitoring/dashboard
   - View recent events with bearing angles and GPS coordinates
   - Monitor active nodes and detection statistics

3. **Test API Endpoints**:
```bash
# Health check
curl http://localhost:8000/edge_client/health

# Get active detection config
curl http://localhost:8000/edge_client/api/detection-config/active

# Get events
curl http://localhost:8000/monitoring/api/events/
```

## Troubleshooting

### Issue: Redis connection error
**Solution**: Ensure Redis is running:
```bash
redis-cli ping
```

### Issue: ngrok tunnel not working
**Solution**: 
- Check that Django server is running on port 8000
- Verify ngrok is authenticated: `ngrok config check`
- Check firewall settings

### Issue: ML model not loading
**Solution**:
- Verify `drone_33d_mlp.onnx` exists in the project directory
- Check that onnxruntime is installed: `pip list | grep onnxruntime`
- Check Django logs for error messages

### Issue: GPS coordinates not showing
**Solution**:
- Ensure you're accessing via HTTPS (use ngrok URL)
- Grant location permissions in your browser
- Check that edge clients are sending GPS data in webhook payloads

### Issue: Static files not loading
**Solution**:
```bash
python manage.py collectstatic --clear
python manage.py collectstatic
```

### Issue: Database errors
**Solution**:
```bash
# Reset database (WARNING: This deletes all data)
rm db.sqlite3
python manage.py migrate
python manage.py init_detection_configs
```

## Production Deployment Notes

For production deployment:

1. **Security**:
   - Set `DEBUG=False` in `.env`
   - Change `SECRET_KEY` to a secure random value
   - Update `ALLOWED_HOSTS` with your domain
   - Use PostgreSQL instead of SQLite
   - Enable HTTPS

2. **Database**:
   - Use PostgreSQL for production
   - Set up database backups
   - Configure connection pooling

3. **Server**:
   - Use Gunicorn or uWSGI instead of Django development server
   - Set up nginx as reverse proxy
   - Configure systemd services for auto-start

4. **Celery**:
   - Use production Redis setup (Redis Sentinel/Cluster)
   - Configure worker concurrency
   - Set up monitoring (Flower)

## Additional Resources

- Django Documentation: https://docs.djangoproject.com/
- ngrok Documentation: https://ngrok.com/docs
- Celery Documentation: https://docs.celeryproject.org/
- ONNX Runtime: https://onnxruntime.ai/

## Support

For issues or questions, please check the project README or contact the development team.

