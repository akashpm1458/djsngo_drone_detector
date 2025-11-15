# EchoShield Django - Acoustic Drone Detection System

A complete Django implementation of the EchoShield distributed edge-deployed acoustic drone detection system for tactical ISR-to-C2 environments.

## Overview

EchoShield is a browser-based acoustic drone detection system that uses:
- **Edge Detection**: Mobile devices running ONNX.js ML inference
- **Node Registry**: In-memory tracking of active edge nodes
- **GCC-PHAT Bearing Estimation**: Multi-node TDOA-based bearing calculation
- **WirePacket Protocol**: Compact wire format for low-bandwidth transmission
- **Real-time Dashboard**: Django-based monitoring interface
- **Background Processing**: Celery tasks for aggregation and deduplication

## Features

### Edge Client (`edge_client` app)
- ✅ Webhook endpoint for edge detection events
- ✅ In-memory node registry (tracks active nodes and detections)
- ✅ GCC-PHAT bearing estimation using TDOA
- ✅ GPS location handling
- ✅ Node status endpoint
- ✅ Browser-based detection UI (template provided)

### Monitoring (`monitoring` app)
- ✅ Ingest API for WirePacket events
- ✅ Wire codec (WirePacket ↔ Canonical Event conversion)
- ✅ Event storage with Django ORM
- ✅ Real-time monitoring dashboard
- ✅ REST API endpoints (DRF)
- ✅ KPI metrics and statistics

### Background Processing (Celery)
- ✅ **Track Aggregation**: Cluster multi-node detections into unified tracks
- ✅ **Event Deduplication**: Flag duplicate events from same node
- ✅ **Track Cleanup**: Mark expired tracks

### Core Models
- ✅ **Event**: Detection events with full metadata
- ✅ **Track**: Aggregated multi-node detection tracks
- ✅ **TrackContributor**: Links events to tracks

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│         EDGE LAYER (Mobile Browser)                     │
│  - ONNX.js ML inference                                 │
│  - GPS location capture                                 │
│  - POST /webhook/edge                                   │
└────────────┬────────────────────────────────────────────┘
             │ WirePacket JSON
             ↓
┌─────────────────────────────────────────────────────────┐
│         EDGE CLIENT APP (Django)                        │
│  - Webhook receiver                                     │
│  - Node registry (in-memory)                            │
│  - GCC-PHAT bearing estimation                          │
│  - Forwards to Ingest API                               │
└────────────┬────────────────────────────────────────────┘
             │ WirePacket → Canonical Event
             ↓
┌─────────────────────────────────────────────────────────┐
│         MONITORING APP (Django)                         │
│  - Ingest API endpoint                                  │
│  - Event storage (Django ORM)                           │
│  - Dashboard views                                      │
│  - REST API (DRF)                                       │
└────────────┬────────────────────────────────────────────┘
             │ Celery Tasks
             ↓
┌─────────────────────────────────────────────────────────┐
│         BACKGROUND PROCESSING (Celery)                  │
│  - Track aggregation (every 30s)                        │
│  - Event deduplication (every 60s)                      │
│  - Track cleanup (every 5min)                           │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.9+
- Redis (for Celery broker)
- SQLite (default) or PostgreSQL (production)

### Installation

1. **Clone the repository**:
```bash
cd django_echoshield
```

2. **Run the setup script**:
```bash
chmod +x start_dev.sh
./start_dev.sh
```

This will:
- Create a virtual environment
- Install dependencies
- Create `.env` file from example
- Run database migrations
- Create a default superuser (`admin` / `admin123`)
- Collect static files

3. **Start the services**:

**Terminal 1 - Django server**:
```bash
./start_django.sh
# Or manually:
# source venv/bin/activate
# python manage.py runserver 0.0.0.0:8000
```

**Terminal 2 - Celery worker & beat**:
```bash
./start_celery.sh
# Or manually:
# source venv/bin/activate
# celery -A echoshield worker -l info &
# celery -A echoshield beat -l info
```

**Terminal 3 - Redis** (if not already running):
```bash
redis-server
```

### Access the Application

- **Edge Detection UI**: http://localhost:8000/
- **Monitoring Dashboard**: http://localhost:8000/api/dashboard/
- **Admin Interface**: http://localhost:8000/admin/ (admin / admin123)
- **REST API**: http://localhost:8000/api/v0/
- **Health Check**: http://localhost:8000/health

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# Database (SQLite by default)
DATABASE_PATH=db.sqlite3

# For PostgreSQL in production:
USE_POSTGRES=True
POSTGRES_DB=echoshield
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# EchoShield Configuration
INGEST_URL=http://localhost:8000/api/v0/ingest/wire
NODE_RETENTION_SECONDS=60
GCC_PHAT_MAX_RADIUS_M=100.0
SPEED_OF_SOUND=343.0
AGGREGATION_WINDOW_NS=10000000000
MIN_TRACK_CONTRIBUTORS=2
```

### Django Settings

Key settings in `echoshield/settings.py`:

- **ECHOSHIELD**: Custom configuration dictionary
- **CELERY_BROKER_URL**: Redis broker for Celery
- **REST_FRAMEWORK**: DRF configuration
- **CORS_ALLOWED_ORIGINS**: CORS settings for edge clients

## API Endpoints

### Edge Client API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/whoami` | GET | Service info |
| `/webhook/edge` | POST | Edge detection webhook |
| `/nodes/status` | GET | Node registry status |
| `/geo-test` | GET | GPS permission test page |
| `/` | GET | Edge detection UI |

**Example: Send detection event**:
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

### Monitoring API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/v0/ingest/wire` | POST | Ingest WirePacket |
| `/api/v0/events/` | GET | List events |
| `/api/v0/events/{id}/` | GET | Event detail |
| `/api/v0/events/stats/` | GET | Event statistics |
| `/api/v0/tracks/` | GET | List tracks |
| `/api/v0/tracks/{id}/` | GET | Track detail |
| `/api/v0/tracks/active/` | GET | Active tracks only |
| `/api/dashboard/` | GET | Dashboard view |
| `/api/dashboard/events/` | GET | Events JSON API |

**Example: Get event statistics**:
```bash
curl http://localhost:8000/api/v0/events/stats/
```

**Response**:
```json
{
  "total_events": 150,
  "active_nodes": 3,
  "events_by_latency_status": {
    "normal": 120,
    "delayed": 25,
    "obsolete": 5
  },
  "events_by_validity": {
    "valid": 140,
    "invalid": 5,
    "unknown": 5
  },
  "duplicate_count": 5
}
```

## Data Models

### Event Model

Stores individual detection events:

```python
class Event(models.Model):
    event_id = models.CharField(max_length=255, unique=True)
    sensor_type = models.CharField(max_length=20)  # acoustic, vision, hybrid
    sensor_node_id = models.CharField(max_length=255)

    # Timestamps (nanoseconds)
    ts_ns = models.BigIntegerField()  # Detection timestamp
    rx_ns = models.BigIntegerField()  # Server receipt timestamp
    latency_ns = models.BigIntegerField()
    latency_status = models.CharField(max_length=20)  # normal, delayed, obsolete

    # Location
    lat = models.FloatField()
    lon = models.FloatField()
    error_radius_m = models.FloatField()

    # Bearing
    bearing_deg = models.FloatField()  # 0-360 degrees
    bearing_conf = models.FloatField()  # 0.0-1.0

    # Post-processing
    validity_status = models.CharField(max_length=20)
    duplicate_flag = models.BooleanField()
    object_track_id = models.CharField(max_length=255)  # FK to Track

    # GCC-PHAT metadata (JSON)
    gcc_phat_metadata = models.JSONField()

    # Audit
    raw_wire_json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
```

### Track Model

Aggregated multi-node detection tracks:

```python
class Track(models.Model):
    track_id = models.CharField(max_length=255, primary_key=True)
    method = models.CharField(max_length=50)  # bearing_only, triangulation

    # Time range
    first_ts_ns = models.BigIntegerField()
    last_ts_ns = models.BigIntegerField()

    # Aggregated position
    aggregated_bearing_deg = models.FloatField()
    aggregation_conf = models.FloatField()

    status = models.CharField(max_length=20)  # active, expired
```

### TrackContributor Model

Links events to tracks:

```python
class TrackContributor(models.Model):
    track = models.ForeignKey(Track)
    event = models.ForeignKey(Event)
    sensor_node_id = models.CharField(max_length=255)
    bearing_deg = models.FloatField()
    ts_ns = models.BigIntegerField()
```

## Background Tasks

### Track Aggregation (`aggregate_tracks`)

Runs every **30 seconds**.

- Clusters events by 10-second time windows
- Requires ≥2 distinct nodes
- Calculates circular mean bearing
- Creates or updates Track objects
- Links events via TrackContributor

### Event Deduplication (`deduplicate_events`)

Runs every **60 seconds**.

Marks duplicates based on:
- Same `sensor_node_id`
- Time delta ≤ 5 seconds
- Bearing difference ≤ 20° (circular)

### Track Cleanup (`cleanup_expired_tracks`)

Runs every **5 minutes**.

Marks tracks as `expired` if:
- Status is `active`
- Last update > 1 minute ago

## Development

### Project Structure

```
django_echoshield/
├── echoshield/              # Django project settings
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   ├── wsgi.py
│   └── asgi.py
├── core/                    # Core models and utilities
│   ├── models.py            # Event, Track, TrackContributor
│   ├── admin.py
│   └── management/commands/
│       └── setup_echoshield.py
├── edge_client/             # Edge client app
│   ├── views.py             # Webhook handler
│   ├── urls.py
│   ├── node_registry.py     # In-memory node tracking
│   ├── gcc_phat_bearing.py  # TDOA bearing estimation
│   └── mappers.py           # Payload → WirePacket
├── monitoring/              # Monitoring & ingest app
│   ├── views.py             # Ingest API, dashboard
│   ├── urls.py
│   ├── serializers.py       # DRF serializers
│   ├── wire_codec.py        # WirePacket ↔ Canonical
│   └── tasks.py             # Celery tasks
├── templates/
│   ├── edge_client/
│   │   └── index.html
│   └── monitoring/
│       └── dashboard.html
├── static/
│   └── edge_client/         # Copy ONNX model and JS here
├── manage.py
├── requirements.txt
├── .env.example
├── start_dev.sh
├── start_django.sh
└── start_celery.sh
```

### Running Tests

```bash
python manage.py test
```

### Database Migrations

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Show migrations
python manage.py showmigrations
```

### Admin Interface

Access the Django admin at http://localhost:8000/admin/

Default credentials (created by `setup_echoshield`):
- Username: `admin`
- Password: `admin123`

**IMPORTANT**: Change these credentials in production!

## Deployment

### Production Checklist

1. **Security**:
   - [ ] Change `SECRET_KEY`
   - [ ] Set `DEBUG=False`
   - [ ] Update `ALLOWED_HOSTS`
   - [ ] Change admin password
   - [ ] Enable HTTPS
   - [ ] Configure CORS properly

2. **Database**:
   - [ ] Switch to PostgreSQL
   - [ ] Set up backups
   - [ ] Configure connection pooling

3. **Celery**:
   - [ ] Use production broker (Redis Sentinel/Cluster)
   - [ ] Configure worker concurrency
   - [ ] Set up monitoring (Flower)

4. **Static Files**:
   - [ ] Run `collectstatic`
   - [ ] Configure CDN/S3 for static files
   - [ ] Enable compression

5. **Server**:
   - [ ] Use Gunicorn/uWSGI
   - [ ] Configure nginx reverse proxy
   - [ ] Set up systemd services
   - [ ] Configure logging

### Example Production Setup

**Gunicorn**:
```bash
gunicorn echoshield.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
```

**Celery Worker**:
```bash
celery -A echoshield worker \
  --loglevel=info \
  --concurrency=4 \
  --max-tasks-per-child=1000
```

**Celery Beat**:
```bash
celery -A echoshield beat \
  --loglevel=info \
  --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

## Integration with Original System

To integrate with your existing EchoShield components:

1. **Copy edge detection files**:
```bash
# Copy ONNX model and config
cp ../edge_webapp_adapter/edge_artifacts/* static/edge_client/

# Copy JavaScript detection logic
cp ../edge_webapp_adapter/app.v4.js static/edge_client/

# Update index.html to reference these files
```

2. **Update webhook URLs**:
   - Edge clients should POST to: `http://your-django-server:8000/webhook/edge`
   - Adapter forwards to: `http://your-django-server:8000/api/v0/ingest/wire`

3. **Migrate existing data** (if needed):
```python
# Create a management command to import existing SQLite events
python manage.py import_events --source ../ingest_api/events.db
```

## Troubleshooting

### Common Issues

**1. Celery tasks not running**:
- Check Redis is running: `redis-cli ping`
- Verify Celery worker is running: `celery -A echoshield inspect active`
- Check Celery beat scheduler: `celery -A echoshield inspect scheduled`

**2. GPS not working on mobile**:
- Ensure you're using HTTPS (required for geolocation API)
- Check browser permissions
- Use ngrok for development: `ngrok http 8000`

**3. Database errors**:
```bash
# Reset database
rm db.sqlite3
python manage.py migrate
python manage.py setup_echoshield
```

**4. Static files not loading**:
```bash
python manage.py collectstatic --clear
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests: `python manage.py test`
4. Submit a pull request

## License

[Your License Here]

## Credits

Built for EDTH Berlin 2025 Hackathon.

Based on the original EchoShield FastAPI/Streamlit implementation.

## Contact

For questions or support, please contact [your email/team].
