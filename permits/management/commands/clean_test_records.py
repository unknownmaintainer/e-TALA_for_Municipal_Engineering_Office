from django.core.management.base import BaseCommand
from django.db.models import Q
from django.core.cache import cache
from permits.models import EngineeringRecord, Document, AuditLog
import logging

logger = logging.getLogger('permits')


class Command(BaseCommand):
    help = 'Cleans up obvious dummy and test records created during development/testing while keeping realistic sample records intact.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='List the matching dummy/test records without deleting them',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)

        test_keywords = [
            'gegeg', 'wwwwww', 'river banks', 'test', 'dummy', 'asdf', 'sample test',
            'testing', '123456', 'foobar', 'lorem', 'fake', 'trial', 'temp record',
            '43333333', 'qwert', 'sample dummy'
        ]

        q_filter = Q()
        for kw in test_keywords:
            q_filter |= Q(title__icontains=kw)
            q_filter |= Q(description__icontains=kw)
            q_filter |= Q(permit_detail__applicant_name__icontains=kw)
            q_filter |= Q(permit_detail__permit_number__icontains=kw)
            q_filter |= Q(project_detail__contractor__icontains=kw)

        # Also include all records currently in Trash/Archived status that were moved during testing
        q_filter |= Q(status='archived')

        matching_records = EngineeringRecord.objects.filter(q_filter).distinct()
        count = matching_records.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No dummy/test records found. Database is already clean!"))
            return

        self.stdout.write(self.style.NOTICE(f"Found {count} dummy/test records eligible for cleanup:"))
        for r in matching_records:
            self.stdout.write(f"  - [ID #{r.record_id}] [{r.record_type}] '{r.title}' (Status: {r.status}, Brgy: {r.barangay.barangay_name})")

        if dry_run:
            self.stdout.write(self.style.WARNING(f"\n[DRY RUN] {count} records would be removed."))
            return

        deleted_records = 0
        deleted_docs = 0

        for r in matching_records:
            rec_id = r.record_id
            rec_title = r.title

            # Delete physical document files
            for doc in r.documents.all():
                if doc.file:
                    try:
                        doc.file.delete(save=False)
                        deleted_docs += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete document file for doc #{doc.document_id}: {e}")

            # Clean up audit log references for this test record
            AuditLog.objects.filter(target_record_id=rec_id).delete()
            AuditLog.objects.filter(action__icontains=f"#{rec_id}").delete()
            AuditLog.objects.filter(action__icontains=f"trash_exp_{rec_id}").delete()

            # Delete record (Cascades to PermitDetail, ProjectDetail, RecordRequirement, Document)
            r.delete()
            deleted_records += 1

        # Clear global cache
        cache.clear()

        self.stdout.write(self.style.SUCCESS(f"\n[SUCCESS] Successfully cleaned {deleted_records} dummy/test records and {deleted_docs} attached files!"))
