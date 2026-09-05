import os
from django.conf import settings
from django.core.management.base import BaseCommand
from permits.models import CustomUser


class Command(BaseCommand):
    help = 'Seeds only the single initial administrator account securely via environment variables'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-insecure-dev',
            action='store_true',
            help='Allows fallback default test password in development mode only.'
        )

    def handle(self, *args, **options):
        is_debug = getattr(settings, 'DEBUG', False)
        admin_email = os.environ.get('SEED_ADMIN_EMAIL')
        admin_username = os.environ.get('SEED_ADMIN_USERNAME', 'admin')
        admin_name = os.environ.get('SEED_ADMIN_FULL_NAME', 'Administrator')
        admin_pass = os.environ.get('SEED_ADMIN_PASSWORD') or os.environ.get('INITIAL_ADMIN_PASSWORD')

        if not admin_pass:
            if is_debug:
                self.stdout.write(self.style.WARNING(
                    "⚠️ [SEED NOTICE] SEED_ADMIN_PASSWORD is not set in .env. "
                    "Please set SEED_ADMIN_PASSWORD in your .env file to create the administrator."
                ))
                return
            else:
                self.stdout.write(self.style.WARNING(
                    "⚠️ [SECURITY NOTICE] Production mode detected (DEBUG=False). "
                    "SEED_ADMIN_PASSWORD was not provided in environment variables. "
                    "Skipping automatic admin creation. Please use 'python manage.py createsuperuser' or set SEED_ADMIN_PASSWORD."
                ))
                return

        if not admin_email:
            self.stdout.write(self.style.ERROR("❌ SEED_ADMIN_EMAIL is required to seed the administrator account."))
            return

        user = CustomUser.objects.filter(email=admin_email).first()
        if not user:
            user = CustomUser.objects.filter(username=admin_username).first()

        if user:
            # User already exists: ensure superuser and admin role are intact without overwriting password
            user.is_staff = True
            user.is_superuser = True
            user.role = 'admin'
            user.save(update_fields=['is_staff', 'is_superuser', 'role'])
            self.stdout.write(self.style.NOTICE(f"Admin account already exists: {user.username} ({user.email})"))
        else:
            user = CustomUser.objects.create_user(
                username=admin_username,
                email=admin_email,
                password=admin_pass,
                role='admin',
                is_staff=True,
                is_superuser=True,
                full_name=admin_name
            )
            self.stdout.write(self.style.SUCCESS(f"Successfully created initial Admin account: {user.username} ({user.email})"))



