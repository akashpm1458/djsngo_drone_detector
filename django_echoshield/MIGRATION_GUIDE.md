# Migration Guide: FastAPI to Django

This guide helps you migrate from the original FastAPI/Streamlit EchoShield implementation to the Django version.

## Key Differences

### 1. Web Framework

**Original**:
- FastAPI for edge_webapp_adapter
- FastAPI for ingest_api
- Streamlit for UI
- Multiple separate processes

**Django**:
- Single Django project with multiple apps
- Django REST Framework for APIs
- Django templates for UI
- Celery for background tasks
- Unified admin interface

### 2. Project Structure Mapping

| Original | Django Equivalent | Notes |
|----------|------------------|-------|
| `edge_webapp_adapter/main.py` | `edge_client/views.py` | Webhook handler |
| `edge_webapp_adapter/mappers.py` | `edge_client/mappers.py` | Same logic |
| `edge_webapp_adapter/node_registry.py` | `edge_client/node_registry.py` | Same implementation |
| `edge_webapp_adapter/gcc_phat_bearing.py` | `edge_client/gcc_phat_bearing.py` | Same algorithm |
| `ingest_api/app.py` | `monitoring/views.py` | Ingest endpoint |
| `ingest_api/schemas.py` | `monitoring/serializers.py` | Pydantic → DRF |
| `ingest_api/wire_codec.py` | `monitoring/wire_codec.py` | Same logic |
| `ingest_api/store/models.sql` | `core/models.py` | SQL → Django ORM |
| `scripts/aggregator.py` | `monitoring/tasks.py::aggregate_tracks` | Standalone → Celery |
| `scripts/dedup_validity.py` | `monitoring/tasks.py::deduplicate_events` | Standalone → Celery |
| `ui/app.py` | `templates/monitoring/dashboard.html` | Streamlit → Django template |

### 3. Endpoint Mapping

| Original Endpoint | Django Endpoint | App |
|------------------|----------------|-----|
| `GET /health` (adapter) | `GET /health` | edge_client |
| `POST /webhook/edge` | `POST /webhook/edge` | edge_client |
| `GET /nodes/status` | `GET /nodes/status` | edge_client |
| `GET /health` (ingest) | `GET /api/health` | monitoring |
| `POST /api/v0/ingest/wire` | `POST /api/v0/ingest/wire` | monitoring |
| N/A | `GET /api/v0/events/` | monitoring (new) |
| N/A | `GET /api/v0/tracks/` | monitoring (new) |
| Streamlit app (port 8501) | `GET /api/dashboard/` | monitoring |

### 4. Configuration

**Original (.env files + config.yaml)**:
```
# edge_webapp_adapter/config.yaml
INGEST_URL: "http://localhost:8080/api/v0/ingest/wire"

# Environment variables scattered
INGEST_DB=/path/to/events.db
```

**Django (single .env file)**:
```bash
# All configuration in one place
INGEST_URL=http://localhost:8000/api/v0/ingest/wire
DATABASE_PATH=db.sqlite3

# EchoShield settings
NODE_RETENTION_SECONDS=60
GCC_PHAT_MAX_RADIUS_M=100.0
```

### 5. Database Access

**Original (raw SQL)**:
```python
import sqlite3
conn = sqlite3.connect('events.db')
cursor = conn.cursor()
cursor.execute("INSERT INTO events ...")
```

**Django (ORM)**:
```python
from core.models import Event
event = Event.objects.create(
    event_id=canonical['event_id'],
    sensor_type=canonical['sensor_type'],
    ...
)
```

### 6. Background Processing

**Original (manual scripts)**:
```bash
python scripts/aggregator.py
python scripts/dedup_validity.py
```

**Django (Celery tasks)**:
```python
# Automatic periodic execution
# Configured in echoshield/celery.py:

app.conf.beat_schedule = {
    'aggregate-tracks-every-30-seconds': {
        'task': 'monitoring.tasks.aggregate_tracks',
        'schedule': 30.0,
    },
}
```

## Migration Steps

### Step 1: Set Up Django Project

```bash
cd django_echoshield
./start_dev.sh
```

### Step 2: Migrate Existing Data (Optional)

If you have existing events in the FastAPI database:

**Option A: Export/Import via JSON**
```bash
# Export from original system
cd ../ingest_api
python -c "
import sqlite3
import json
conn = sqlite3.connect('events.db')
cursor = conn.cursor()
cursor.execute('SELECT * FROM events')
rows = cursor.fetchall()
# ... export to JSON
"

# Import into Django
cd ../django_echoshield
python manage.py shell
```

```python
# In Django shell
import json
from core.models import Event

with open('exported_events.json') as f:
    data = json.load(f)
    for item in data:
        Event.objects.create(**item)
```

**Option B: Create a custom management command**

Create `core/management/commands/import_events.py`:

```python
from django.core.management.base import BaseCommand
import sqlite3
from core.models import Event

class Command(BaseCommand):
    help = 'Import events from original SQLite database'

    def add_arguments(self, parser):
        parser.add_argument('--source', type=str, required=True)

    def handle(self, *args, **options):
        source_db = options['source']
        conn = sqlite3.connect(source_db)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM events")
        rows = cursor.fetchall()

        for row in rows:
            # Map columns to Event model fields
            Event.objects.get_or_create(
                event_id=row[1],  # Adjust indices based on your schema
                defaults={
                    'sensor_type': row[2],
                    # ... map all fields
                }
            )
        self.stdout.write(f"Imported {len(rows)} events")
```

Run:
```bash
python manage.py import_events --source ../ingest_api/events.db
```

### Step 3: Copy Static Files

```bash
# Copy edge detection assets
cp ../edge_webapp_adapter/edge_artifacts/* static/edge_client/
cp ../edge_webapp_adapter/app.v4.js static/edge_client/
cp ../edge_webapp_adapter/index.html templates/edge_client/
```

### Step 4: Update Edge Clients

Update webhook URLs in edge devices:

**Before**:
```javascript
const webhookUrl = 'http://localhost:8000/webhook/edge';
```

**After** (same URL, but Django backend):
```javascript
const webhookUrl = 'http://localhost:8000/webhook/edge';
```

No changes needed if using the same port!

### Step 5: Update Environment Configuration

**Before** (multiple files):
```
edge_webapp_adapter/config.yaml
ingest_api/.env
ui/.env
```

**After** (single file):
```
django_echoshield/.env
```

### Step 6: Start Services

**Before** (3+ terminals):
```bash
# Terminal 1
cd edge_webapp_adapter
uvicorn main:app --port 8000

# Terminal 2
cd ingest_api
uvicorn app:app --port 8080

# Terminal 3
cd ui
streamlit run app.py

# Terminal 4
python scripts/aggregator.py  # Manual execution
```

**After** (2 terminals):
```bash
# Terminal 1
./start_django.sh

# Terminal 2
./start_celery.sh  # Automatic background tasks
```

## Code Migration Examples

### Example 1: Webhook Handler

**Original (FastAPI)**:
```python
@app.post("/webhook/edge")
async def webhook_edge(request: Request):
    payload = await request.json()
    wire = to_wirepacket(payload)

    async with httpx.AsyncClient() as client:
        r = await client.post(INGEST_URL, json=wire)

    return {"forwarded": True, "event_id": wire["event_id"]}
```

**Django**:
```python
@method_decorator(csrf_exempt, name='dispatch')
class WebhookEdgeView(View):
    async def post(self, request):
        payload = json.loads(request.body)
        wire_packet = to_wirepacket(payload)

        async with httpx.AsyncClient() as client:
            response = await client.post(ingest_url, json=wire_packet)

        return JsonResponse({
            'forwarded': True,
            'event_id': wire_packet['event_id']
        }, status=202)
```

### Example 2: Ingest Endpoint

**Original (FastAPI + Pydantic)**:
```python
@app.post("/api/v0/ingest/wire")
async def ingest_wire(wire: WirePacketIn):
    rx_ns = time.time_ns()
    canonical = wire_codec.to_canonical(wire, rx_ns)

    # Raw SQL insert
    cursor.execute("INSERT INTO events (...) VALUES (...)")

    return {"status": "accepted", "event_id": canonical["event_id"]}
```

**Django (DRF + ORM)**:
```python
class IngestWireView(View):
    def post(self, request):
        wire_packet = json.loads(request.body)
        serializer = WirePacketSerializer(data=wire_packet)

        if not serializer.is_valid():
            return JsonResponse({'errors': serializer.errors}, status=400)

        rx_ns = get_current_time_ns()
        canonical = to_canonical(serializer.validated_data, rx_ns)

        # Django ORM
        event = Event.objects.create(**canonical)

        return JsonResponse({
            'status': 'accepted',
            'event_id': event.event_id
        }, status=202)
```

### Example 3: Background Processing

**Original (standalone script)**:
```python
# scripts/aggregator.py
if __name__ == '__main__':
    while True:
        aggregate_tracks()
        time.sleep(30)
```

**Django (Celery task)**:
```python
# monitoring/tasks.py
@shared_task
def aggregate_tracks():
    # Same logic, but runs automatically via Celery Beat
    logger.info("Starting track aggregation")
    # ... implementation
    return tracks_created

# Configured in echoshield/celery.py to run every 30 seconds
```

## Testing Your Migration

### 1. Test Edge Webhook

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

Expected response:
```json
{
  "status": "accepted",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "forwarded": true,
  "location_method": "LOC_BEARING_ONLY",
  "bearing_deg": 45.0,
  "gcc_phat": false
}
```

### 2. Verify Event Storage

```bash
python manage.py shell
```

```python
from core.models import Event
Event.objects.count()  # Should show 1
event = Event.objects.first()
print(event.event_id, event.latency_ms, event.bearing_deg)
```

### 3. Check Dashboard

Visit http://localhost:8000/api/dashboard/ and verify:
- KPIs show correct values
- Recent events table displays the test event
- Latency statistics are calculated

### 4. Verify Celery Tasks

```bash
# Check task status
celery -A echoshield inspect active

# Manually trigger tasks for testing
python manage.py shell
```

```python
from monitoring.tasks import aggregate_tracks, deduplicate_events
aggregate_tracks.delay()  # Async
deduplicate_events.apply()  # Synchronous for testing
```

## Rollback Plan

If you need to rollback to the original system:

1. **Stop Django services**:
```bash
# Ctrl+C on Django server
# Ctrl+C on Celery worker
```

2. **Restart original services**:
```bash
cd ../edge_webapp_adapter
uvicorn main:app --port 8000 &

cd ../ingest_api
uvicorn app:app --port 8080 &

cd ../ui
streamlit run app.py &
```

3. **Update edge client URLs** (if changed):
```javascript
const webhookUrl = 'http://localhost:8000/webhook/edge';  // Original
```

## Benefits of Django Migration

1. **Unified Codebase**: Single project vs multiple microservices
2. **Admin Interface**: Built-in admin for data management
3. **ORM Benefits**: Type safety, migrations, query optimization
4. **REST API**: Full-featured API with DRF
5. **Background Tasks**: Automatic scheduling with Celery
6. **Scalability**: Better production deployment options
7. **Testing**: Django's test framework
8. **Documentation**: Auto-generated API docs with DRF
9. **Community**: Larger ecosystem and more resources

## Need Help?

- Check the main README.md for detailed documentation
- Review the original code for comparison
- Test incrementally with curl commands
- Use Django shell for debugging: `python manage.py shell`
- Check logs: `tail -f logs/echoshield.log`
