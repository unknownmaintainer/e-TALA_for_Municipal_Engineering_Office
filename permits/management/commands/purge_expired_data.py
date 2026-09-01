from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import os
import shutil

from permits.models import LoginAttempt, EngineeringRecord, Document, AuditLog


class Command(BaseCommand):
    help = 'Cleans up expired successful login attempts (90 days) and temporary export cache files (24 hours).'

    def handle(self, *args, **options):
        now = timezone.now()
        self.stdout.write(self.style.NOTICE(f"Starting eTala maintenance cleanup at {now}..."))

        # 1. Login History Cleanup (Purge successful logins > 90 days, keep failed/blocked security logs)
        ninety_days_ago = now - timedelta(days=90)
        purged_logins, _ = LoginAttempt.objects.filter(
            success=True,
            timestamp__lt=ninety_days_ago
        ).delete()
        self.stdout.write(self.style.SUCCESS(f"[OK] Purged {purged_logins} routine login attempts older than 90 days."))

        # 2. Clean up temporary export files / ZIP caches (> 24 hours)
        from django.conf import settings
        temp_dir = getattr(settings, 'TEMP_DIR', os.path.join(settings.BASE_DIR, 'tmp'))
        cleaned_files = 0
        if os.path.exists(temp_dir):
            one_day_ago_ts = (now - timedelta(hours=24)).timestamp()
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                try:
                    if os.path.isfile(item_path) and os.path.getmtime(item_path) < one_day_ago_ts:
                        os.remove(item_path)
                        cleaned_files += 1
                except OSError:
                    pass
        self.stdout.write(self.style.SUCCESS(f"[OK] Cleaned {cleaned_files} temporary export cache files."))

        # 3. 30-Day Trash Retention Cleanup
        try:
            from permits.services import purge_expired_trash_records
            res = purge_expired_trash_records(retention_days=30)
            self.stdout.write(self.style.SUCCESS(f"[OK] Purged {res['purged_records']} expired trash records and {res['purged_documents']} attached files (30-day retention)."))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"[WARN] Error during trash auto-purge: {e}"))

        self.stdout.write(self.style.SUCCESS("[OK] Maintenance cleanup completed successfully."))
