from django.core.management.base import BaseCommand
from permits.models import CustomUser


class Command(BaseCommand):
    help = 'Seeds initial municipal staff, engineer, and administrator accounts'

    def handle(self, *args, **options):
        users_data = [
            {
                'username': 'admin',
                'email': 'admin@gmail.com',
                'full_name': 'Administrator',
                'role': 'admin',
                'password': 'admin123',
                'is_superuser': True,
                'is_staff': True
            },
            {
                'username': 'staff',
                'email': 'staff@gmail.com',
                'full_name': 'Engineering Staff',
                'role': 'staff',
                'password': 'password123',
                'is_superuser': False,
                'is_staff': True
            },
            {
                'username': 'engineer',
                'email': 'staff1@gmail.com',
                'full_name': 'Engr. Maria Santos',
                'role': 'staff',
                'designation': 'Municipal Engineer',
                'password': 'password123',
                'is_superuser': False,
                'is_staff': True
            }
        ]

        for ud in users_data:
            user = CustomUser.objects.filter(email=ud['email']).first()
            if not user:
                user = CustomUser.objects.filter(username=ud['username']).first()

            if user:
                # Do NOT overwrite existing password or user-customized profile
                self.stdout.write(self.style.NOTICE(f"User already exists, preserving data: {user.username} ({user.email})"))
            else:
                user = CustomUser.objects.create_user(
                    username=ud['username'],
                    email=ud['email'],
                    password=ud['password'],
                    role=ud['role'],
                    is_staff=ud['is_staff'],
                    is_superuser=ud['is_superuser'],
                    full_name=ud['full_name']
                )
                if 'designation' in ud:
                    user.designation = ud['designation']
                    user.save(update_fields=['designation'])
                self.stdout.write(self.style.SUCCESS(f"Created default user: {user.username} ({user.email})"))

