#!/bin/bash
# Start Celery worker and beat scheduler

source venv/bin/activate

# Start Celery worker in background
celery -A echoshield worker -l info &
WORKER_PID=$!

# Start Celery beat in background
celery -A echoshield beat -l info &
BEAT_PID=$!

echo "Celery worker PID: $WORKER_PID"
echo "Celery beat PID: $BEAT_PID"
echo "Press Ctrl+C to stop..."

# Wait for interrupt
trap "kill $WORKER_PID $BEAT_PID; exit" INT
wait
