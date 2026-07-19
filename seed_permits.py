import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'etala_project.settings')
django.setup()

from permits.models import CustomUser, Barangay, Category, Record, Document

def seed_data():
    print("Seeding Engineering Records Management database...")

    # 1. Create Users
    users_data = [
        {
            'username': 'admin',
            'email': 'admin@gmail.com',
            'full_name': 'Rostom Balboa',
            'role': 'admin',
            'password': 'admin123',
            'is_superuser': True,
            'is_staff': True
        },
        {
            'username': 'staff',
            'email': 'staff@gmail.com',
            'full_name': 'Mardion Fuerte',
            'role': 'staff',
            'password': 'password123',
            'is_superuser': False,
            'is_staff': True
        },
        {
            'username': 'engineer',
            'email': 'engineer@gmail.com',
            'full_name': 'Engr. Maria Santos',
            'role': 'engineer',
            'password': 'password123',
            'is_superuser': False,
            'is_staff': True
        }
    ]

    users = {}
    for ud in users_data:
        user = CustomUser.objects.filter(email=ud['email']).first()
        if not user:
            user = CustomUser.objects.filter(username=ud['username']).first()

        if user:
            user.email = ud['email']
            user.username = ud['username']
            user.full_name = ud['full_name']
            user.role = ud['role']
            user.is_staff = ud['is_staff']
            user.is_superuser = ud['is_superuser']
            user.save()
            print(f"Updated user: {user.username} ({user.email})")
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
            print(f"Created user: {user.username} ({user.email})")
        
        users[ud['role']] = user

    # 2. Seed Barangays
    barangays_list = [
        "Bagong Lipunan", "Balilit", "Barayong", "Barugohay Central", "Barugohay Norte", 
        "Barugohay Sur", "Baybay (Poblacion)", "Binibihan", "Bislig", "Caghalo", 
        "Camansi", "Canal", "Candigahub", "Canfabi", "Canlampay", 
        "Cogon", "Cutay", "East Visoria", "Guindapunan East", "Guindapunan West", 
        "Hiluctogan", "Jugaban (Poblacion)", "Libo", "Lower Hiraan", "Lower Sogod", 
        "Macalpi", "Manloy", "Nauguisan", "Paglaum", "Pangna", 
        "Parag-um", "Parena (Parina)", "Piloro", "Ponong (Poblacion)", "Rizal (Tagak East)", 
        "Sagkahan", "San Isidro", "San Juan", "San Mateo (Poblacion)", "Santa Fe", 
        "Sawang (Poblacion)", "Tagak", "Tangnan", "Tigbao", "Tinaguban", 
        "Upper Hiraan", "Upper Sogod", "Uyawan", "West Visoria"
    ]
    
    barangay_objs = {}
    for b_name in barangays_list:
        obj, created = Barangay.objects.get_or_create(barangay_name=b_name)
        if created:
            print(f"Created barangay: {b_name}")
        barangay_objs[b_name] = obj

    # 3. Seed Categories
    categories_list = [
        "Building Permit", "Electrical Permit", "Sanitary Permit", 
        "Mechanical Permit", "Fencing Permit", "Demolition Permit", 
        "Occupancy Permit"
    ]
    
    category_objs = {}
    for c_name in categories_list:
        obj, created = Category.objects.get_or_create(category_name=c_name)
        if created:
            print(f"Created category: {c_name}")
        category_objs[c_name] = obj

    # 4. Seed a test record
    test_record = Record.objects.filter(project_name="Proposed Two-Storey Residence").first()
    if not test_record:
        record = Record.objects.create(
            project_name="Proposed Two-Storey Residence",
            record_title="Proposed Two-Storey Residential Building Construction",
            category=category_objs["Building Permit"],
            location_type="barangay",
            barangay=barangay_objs["Ponong (Poblacion)"],
            year=2026,
            budget_amount=2500000.00,
            archive_number="BP-2026-0012",
            description="Two-storey residential project located in Ponong, Carigara, Leyte.",
            status="active",
            created_by=users["staff"]
        )
        print(f"Created test record: {record.project_name}")

    print("Seeding complete.")

if __name__ == '__main__':
    seed_data()
