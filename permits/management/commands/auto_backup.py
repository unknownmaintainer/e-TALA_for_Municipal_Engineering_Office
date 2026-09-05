from django.core.management.base import BaseCommand
from permits.services import execute_automated_backup


class Command(BaseCommand):
    help = 'Executes the automated eTala Hybrid Smart-Sync Backup (Database Snapshot + Incremental Media Sync + Auto-Retention).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=14,
            help='Snapshot retention period in days (default: 14)',
        )
        parser.add_argument(
            '--target-dir',
            type=str,
            default=None,
            help='Custom target directory for backup vault (defaults to BACKUP_STORAGE_PATH env or BASE_DIR/backups)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate backup execution without writing files or modifying storage',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force backup execution even if a backup was already created today',
        )

    def handle(self, *args, **options):
        retention_days = options.get('days', 14)
        target_dir = options.get('target_dir')
        dry_run = options.get('dry_run', False)
        force = options.get('force', False)

        mode_str = "[DRY-RUN] " if dry_run else ""
        self.stdout.write(self.style.NOTICE(f"{mode_str}Starting eTala Automated Smart-Sync Backup (Retention: {retention_days} days)..."))

        result = execute_automated_backup(
            retention_days=retention_days,
            target_dir=target_dir,
            user=None,
            dry_run=dry_run,
            skip_if_already_backed_up_today=True,
            force=force,
        )

        if result.get('skipped'):
            self.stdout.write(self.style.WARNING(
                f"\n[SKIPPED] {result.get('reason')}\n"
                f"  - Last Backup: {result.get('last_backup_str')}\n"
                f"  - Tip: Use --force to run backup anyway regardless of same-day status.\n"
            ))
        elif result.get('success'):
            self.stdout.write(self.style.SUCCESS(
                f"\n{mode_str}Backup completed successfully!\n"
                f"  - Database Snapshot: {result['db_filename']} ({result['total_records']} records)\n"
                f"  - Incremental Media Synced: {result['new_files_synced']} new/updated files (out of {result['total_media_files']} total)\n"
                f"  - Expired Snapshots Cleaned: {result['purged_snapshots']}\n"
                f"  - Vault Location: {result['backup_dir']}\n"
                f"  - Timestamp: {result['timestamp']}\n"
            ))
        else:
            self.stdout.write(self.style.ERROR(f"\n{mode_str}Backup failed."))
