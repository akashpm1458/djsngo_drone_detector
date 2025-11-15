# EchoShield Django Project
__version__ = '1.0.0'

# Celery app configuration
from .celery import app as celery_app

__all__ = ('celery_app',)
