"""
Celery configuration for EchoShield project.
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'echoshield.settings')

app = Celery('echoshield')

# Load configuration from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()

# Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    'aggregate-tracks-every-30-seconds': {
        'task': 'monitoring.tasks.aggregate_tracks',
        'schedule': 30.0,  # Run every 30 seconds
    },
    'deduplicate-events-every-minute': {
        'task': 'monitoring.tasks.deduplicate_events',
        'schedule': 60.0,  # Run every minute
    },
    'cleanup-expired-tracks-every-5-minutes': {
        'task': 'monitoring.tasks.cleanup_expired_tracks',
        'schedule': 300.0,  # Run every 5 minutes
    },
}


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
