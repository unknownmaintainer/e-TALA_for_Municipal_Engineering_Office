import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'etala_project.settings')
django.setup()

from permits.models import CustomUser, Barangay, Category, Record, Document, EngineeringRecord, UserDevice, PasswordHistory, AuditLog

def seed_data():
    print("Seeding Engineering Records Management database...")

    # 1. Master System Administrator Only
    admin_email = os.environ.get('SEED_ADMIN_EMAIL', 'carigaraetala@gmail.com').strip().lower()
    admin_username = os.environ.get('SEED_ADMIN_USERNAME', 'admin').strip().lower()
    admin_pass = os.environ.get('SEED_ADMIN_PASSWORD') or os.environ.get('INITIAL_ADMIN_PASSWORD')
    if not admin_pass:
        import secrets
        admin_pass = secrets.token_urlsafe(16)


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
        print(f"Verified Master Admin: {admin_user.username} ({admin_user.email})")
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
        print(f"Created Master Admin: {admin_user.username} ({admin_user.email})")

    # Clean up legacy dummy accounts
    dummy_emails = ['staff@gmail.com', 'staff1@gmail.com', 'admin@gmail.com']
    for dummy_email in dummy_emails:
        if dummy_email.lower() == admin_email.lower():
            continue
        for dummy in CustomUser.objects.filter(email__iexact=dummy_email):
            try:
                EngineeringRecord.objects.filter(created_by=dummy).update(created_by=admin_user)
                Document.objects.filter(uploaded_by=dummy).update(uploaded_by=admin_user)
                Record.objects.filter(created_by=dummy).update(created_by=admin_user)
                UserDevice.objects.filter(user=dummy).delete()
                PasswordHistory.objects.filter(user=dummy).delete()
                AuditLog.objects.filter(user=dummy).update(user=admin_user)
                dummy.delete()
                print(f"Purged dummy account: {dummy_email}")
            except Exception as e:
                dummy.is_active = False
                dummy.save(update_fields=['is_active'])
                print(f"Deactivated dummy account: {dummy_email}")

    # 2. Seed Barangays (49 Barangays of Carigara)
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
    
    for b_name in barangays_list:
        Barangay.objects.get_or_create(barangay_name=b_name)

    # 3. Seed Categories
    categories_list = [
        "Building Permit", "Electrical Permit","Fencing Permit", 
        "Occupancy Permit"
    ]
    
    for c_name in categories_list:
        Category.objects.get_or_create(category_name=c_name)

    print("Seeding complete. Master admin verified and all dummy users purged.")

if __name__ == '__main__':
    seed_data()
