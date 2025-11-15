# EchoShield Django - Quick Start Guide

Get up and running with EchoShield Django in 5 minutes!

## Prerequisites

- Python 3.9+
- Redis (for Celery)
- Git

## Installation (3 steps)

### 1. Set up the environment

```bash
cd django_echoshield
chmod +x start_dev.sh
./start_dev.sh
```

This will:
- Create virtual environment
- Install all dependencies
- Set up database
- Create admin user
- Collect static files

### 2. Start the services

**Terminal 1 - Django server**:
```bash
./start_django.sh
```

**Terminal 2 - Celery (background tasks)**:
```bash
# Make sure Redis is running first
redis-server &

# Start Celery
./start_celery.sh
```

### 3. Access the application

Open your browser to:
- **Dashboard**: http://localhost:8000/api/dashboard/
- **Edge Client**: http://localhost:8000/
- **Admin**: http://localhost:8000/admin/ (admin/admin123)

## Test It Out

Send a test detection event:

```bash
curl -X POST http://localhost:8000/webhook/edge \
  -H "Content-Type: application/json" \
  -d '{
    "nodeId": "NODE_TEST_01",
    "time_ms": 1699999999999,
    "azimuth_deg": 45.0,
    "confidence": 0.87,
    "event": "drone",
    "lat": 52.5163,
    "lon": 13.3777,
    "acc_m": 15.0
  }'
```

Then check the dashboard at http://localhost:8000/api/dashboard/ to see your event!

## Next Steps

1. **Configure settings**: Edit `.env` file for your environment
2. **Add edge nodes**: Open http://localhost:8000/ on mobile devices
3. **View data**: Access http://localhost:8000/admin/ to browse events
4. **API access**: Try http://localhost:8000/api/v0/events/
5. **Monitor tasks**: Check Celery logs for background processing

## Common Commands

```bash
# Create admin user
python manage.py createsuperuser

# Run migrations
python manage.py migrate

# Access Django shell
python manage.py shell

# Collect static files
python manage.py collectstatic

# Run tests
python manage.py test

# Check Celery tasks
celery -A echoshield inspect active
```

## Troubleshooting

**Redis not running?**
```bash
redis-server
# Or on macOS:
brew services start redis
```

**Database issues?**
```bash
rm db.sqlite3
python manage.py migrate
python manage.py setup_echoshield
```

**Static files not loading?**
```bash
python manage.py collectstatic --clear
```

## File Structure Overview

```
django_echoshield/
├── edge_client/        # Edge webhook and node registry
├── monitoring/         # Ingest API and dashboard
├── core/              # Shared models (Event, Track)
├── templates/         # HTML templates
├── static/           # Static files (JS, CSS, ONNX model)
├── manage.py         # Django management
└── .env              # Configuration
```

## What's Running?

- **Port 8000**: Django server (edge client + monitoring API)
- **Port 6379**: Redis (Celery broker)
- **Background**: Celery worker (aggregation, deduplication)
- **Background**: Celery beat (task scheduler)

## Quick API Reference

| Endpoint | Description |
|----------|-------------|
| `POST /webhook/edge` | Edge detection webhook |
| `POST /api/v0/ingest/wire` | Ingest WirePacket |
| `GET /api/v0/events/` | List events |
| `GET /api/v0/tracks/` | List tracks |
| `GET /api/dashboard/` | Monitoring dashboard |
| `GET /admin/` | Admin interface |

## Need More Help?

- Read the full **README.md** for detailed documentation
- Check **MIGRATION_GUIDE.md** if migrating from FastAPI
- Review code in `edge_client/` and `monitoring/` apps

## Production Deployment

For production use:

1. Set `DEBUG=False` in `.env`
2. Change `SECRET_KEY` to a random value
3. Update `ALLOWED_HOSTS`
4. Switch to PostgreSQL (set `USE_POSTGRES=True`)
5. Use Gunicorn instead of runserver
6. Set up nginx reverse proxy
7. Configure SSL/HTTPS

See README.md for full production deployment guide.

---

**Happy Detecting! 🚁🔊**
