"""
Management command to set up EchoShield database and initial data.
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Set up EchoShield database and initial data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up EchoShield...'))

        # Run migrations
        self.stdout.write('Running database migrations...')
        call_command('migrate', '--noinput')

        # Create superuser (if not exists)
        self.stdout.write('Creating default superuser (if needed)...')
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@echoshield.local',
                password='admin123'
            )
            self.stdout.write(self.style.SUCCESS(
                'Created superuser: admin / admin123 (CHANGE THIS IN PRODUCTION!)'
            ))

        # Collect static files
        self.stdout.write('Collecting static files...')
        call_command('collectstatic', '--noinput', '--clear')

        self.stdout.write(self.style.SUCCESS('\nEchoShield setup complete!'))
        self.stdout.write(self.style.WARNING('\nNext steps:'))
        self.stdout.write('1. Start the development server: python manage.py runserver')
        self.stdout.write('2. Start Celery worker: celery -A echoshield worker -l info')
        self.stdout.write('3. Start Celery beat: celery -A echoshield beat -l info')
        self.stdout.write('4. Access the dashboard: http://localhost:8000/api/dashboard/')
        self.stdout.write('5. Access the edge client: http://localhost:8000/')
