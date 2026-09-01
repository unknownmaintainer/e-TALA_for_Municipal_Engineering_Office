from django.core.management.base import BaseCommand
from permits.services import purge_expired_trash_records


class Command(BaseCommand):
    help = 'Purges soft-deleted records from Trash that have exceeded the 30-day auto-retention policy.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Retention period in days (default: 30)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate deletion without actually removing records or files',
        )

    def handle(self, *args, **options):
        retention_days = options.get('days', 30)
        dry_run = options.get('dry_run', False)

        mode_str = "DRY RUN: " if dry_run else ""
        self.stdout.write(self.style.NOTICE(f"{mode_str}Purging trash records older than {retention_days} days..."))

        result = purge_expired_trash_records(retention_days=retention_days, dry_run=dry_run)

        purged_records = result['purged_records']
        purged_docs = result['purged_documents']

        if dry_run:
            self.stdout.write(self.style.WARNING(f"[DRY-RUN] Found {purged_records} records ({purged_docs} attached files) eligible for permanent deletion."))
        else:
            self.stdout.write(self.style.SUCCESS(f"[SUCCESS] Permanently purged {purged_records} expired records and {purged_docs} attached files."))
