import os
from django.core.management.base import BaseCommand
from django.conf import settings
from permits.models import Document, CustomUser


class Command(BaseCommand):
    help = "Scans media directories and removes orphan/unreferenced uploaded files not linked in the database."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate cleanup without deleting any files from disk.'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        media_root = settings.MEDIA_ROOT
        
        self.stdout.write(self.style.MIGRATE_HEADING("=== ETALA MEDIA STORAGE CLEANUP ==="))
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE: No files will be deleted."))

        removed_count = 0
        reclaimed_bytes = 0

        # 1. Clean Document Files
        doc_dir = os.path.join(media_root, 'documents')
        if os.path.exists(doc_dir):
            db_doc_files = set()
            for doc in Document.objects.all():
                if doc.file:
                    db_doc_files.add(os.path.basename(str(doc.file)))

            for filename in os.listdir(doc_dir):
                filepath = os.path.join(doc_dir, filename)
                if os.path.isfile(filepath) and filename not in db_doc_files:
                    file_size = os.path.getsize(filepath)
                    reclaimed_bytes += file_size
                    removed_count += 1
                    if not dry_run:
                        os.remove(filepath)
                        self.stdout.write(self.style.SUCCESS(f"Deleted orphan doc: {filename} ({file_size} bytes)"))
                    else:
                        self.stdout.write(f"[DRY-RUN] Would delete orphan doc: {filename} ({file_size} bytes)")

        # 2. Clean Profile Picture Files
        prof_dir = os.path.join(media_root, 'profile_pictures')
        if os.path.exists(prof_dir):
            db_prof_files = set()
            for user in CustomUser.objects.all():
                if user.profile_picture:
                    db_prof_files.add(os.path.basename(str(user.profile_picture)))

            for filename in os.listdir(prof_dir):
                filepath = os.path.join(prof_dir, filename)
                if os.path.isfile(filepath) and filename not in db_prof_files:
                    file_size = os.path.getsize(filepath)
                    reclaimed_bytes += file_size
                    removed_count += 1
                    if not dry_run:
                        os.remove(filepath)
                        self.stdout.write(self.style.SUCCESS(f"Deleted orphan profile picture: {filename} ({file_size} bytes)"))
                    else:
                        self.stdout.write(f"[DRY-RUN] Would delete orphan profile picture: {filename} ({file_size} bytes)")

        # 3. Clean Temp Uploads
        temp_dir = os.path.join(media_root, 'temp_uploads')
        if os.path.exists(temp_dir):
            for filename in os.listdir(temp_dir):
                filepath = os.path.join(temp_dir, filename)
                if os.path.isfile(filepath):
                    file_size = os.path.getsize(filepath)
                    reclaimed_bytes += file_size
                    removed_count += 1
                    if not dry_run:
                        os.remove(filepath)
                        self.stdout.write(self.style.SUCCESS(f"Deleted temp upload: {filename} ({file_size} bytes)"))
                    else:
                        self.stdout.write(f"[DRY-RUN] Would delete temp upload: {filename} ({file_size} bytes)")

        mb_reclaimed = reclaimed_bytes / (1024 * 1024)
        summary_msg = f"Cleanup Complete: {removed_count} orphan file(s) processed, {mb_reclaimed:.2f} MB disk space reclaimed."
        self.stdout.write(self.style.SUCCESS(summary_msg))
