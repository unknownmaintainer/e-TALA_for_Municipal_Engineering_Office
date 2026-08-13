from django.core.management.base import BaseCommand
from permits.services import send_document_expiry_alerts

class Command(BaseCommand):
    help = 'Scans engineering documents for upcoming expiry or expired status and dispatches summary emails.'

    def handle(self, *args, **options):
        self.stdout.write("Scanning documents for upcoming expiration...")
        success, message = send_document_expiry_alerts()
        if success:
            self.stdout.write(self.style.SUCCESS(f"✅ {message}"))
        else:
            self.stdout.write(self.style.WARNING(f"ℹ️ {message}"))
