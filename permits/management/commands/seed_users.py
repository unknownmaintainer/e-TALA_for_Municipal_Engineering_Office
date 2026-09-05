import os
from django.conf import settings
from django.core.management.base import BaseCommand
from permits.models import CustomUser, EngineeringRecord, Document, UserDevice, PasswordHistory, AuditLog


class Command(BaseCommand):
    help = 'Seeds the single master System Administrator account and purges legacy dummy test accounts'

    def handle(self, *args, **options):
        admin_email = os.environ.get('SEED_ADMIN_EMAIL', 'carigaraetala@gmail.com').strip().lower()
        admin_username = os.environ.get('SEED_ADMIN_USERNAME', 'admin').strip().lower()
        admin_name = os.environ.get('SEED_ADMIN_FULL_NAME', 'System Administrator').strip()
        admin_pass = os.environ.get('SEED_ADMIN_PASSWORD') or os.environ.get('INITIAL_ADMIN_PASSWORD') or 'eTala@2026'

        # 1. Ensure Master System Administrator exists
        admin_user = CustomUser.objects.filter(email=admin_email).first()
        if not admin_user:
            admin_user = CustomUser.objects.filter(username=admin_username).first()

        if admin_user:
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.role = 'admin'
            admin_user.full_name = admin_name
            admin_user.designation = 'System Administrator'
            admin_user.email = admin_email
            admin_user.save(update_fields=['is_staff', 'is_superuser', 'role', 'full_name', 'designation', 'email'])
            self.stdout.write(self.style.SUCCESS(f"Verified Master Admin: {admin_user.username} ({admin_user.email})"))
        else:
            admin_user = CustomUser.objects.create_user(
                username=admin_username,
                email=admin_email,
                password=admin_pass,
                role='admin',
                is_staff=True,
                is_superuser=True,
                full_name=admin_name,
                designation='System Administrator'
            )
            self.stdout.write(self.style.SUCCESS(f"Successfully created Master Admin: {admin_user.username} ({admin_user.email})"))

        # 2. Automatically purge dummy seeded test accounts
        dummy_emails = ['staff@gmail.com', 'staff1@gmail.com', 'admin@gmail.com']
        for dummy_email in dummy_emails:
            if dummy_email.lower() == admin_email.lower():
                continue
            dummies = CustomUser.objects.filter(email__iexact=dummy_email)
            for dummy in dummies:
                target_name = dummy.full_name or dummy.username
                try:
                    # Reassign records/documents to master admin
                    EngineeringRecord.objects.filter(created_by=dummy).update(created_by=admin_user)
                    Document.objects.filter(uploaded_by=dummy).update(uploaded_by=admin_user)
                    UserDevice.objects.filter(user=dummy).delete()
                    PasswordHistory.objects.filter(user=dummy).delete()
                    AuditLog.objects.filter(user=dummy).update(user=admin_user)
                    dummy.delete()
                    self.stdout.write(self.style.SUCCESS(f"Purged dummy account: {target_name} ({dummy_email})"))
                except Exception as e:
                    dummy.is_active = False
                    dummy.save(update_fields=['is_active'])
                    self.stdout.write(self.style.WARNING(f"Deactivated dummy account {dummy_email}: {e}"))
