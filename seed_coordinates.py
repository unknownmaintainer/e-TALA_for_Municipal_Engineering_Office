import os
import django
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'etala_project.settings')
django.setup()

from permits.models import Barangay, EngineeringRecord

# Representative Carigara, Leyte Barangay coordinates
CARIGARA_BARANGAY_COORDS = {
    'Poblacion Jugaban': (11.3005, 124.6880),
    'Poblacion Ponong': (11.3040, 124.6920),
    'Poblacion Baybay': (11.3060, 124.6850),
    'Sawang': (11.2980, 124.6950),
    'Guinte': (11.3120, 124.6750),
    'Barugohay Norte': (11.3250, 124.7010),
    'Barugohay Sur': (11.3180, 124.7080),
    'Tangnan': (11.2850, 124.6600),
    'Uyawan': (11.2910, 124.6780),
    'Macalagwang': (11.2780, 124.6920),
    'Manloy': (11.3150, 124.6650),
    'Sagkahan': (11.3080, 124.6980),
    'Libo': (11.2940, 124.6820),
    'San Mateo': (11.3190, 124.6890),
    'Paglaum': (11.3030, 124.6860),
    'Santa Fe': (11.2890, 124.7040),
}

base_lat = 11.3021
base_lng = 124.6897

print("Seeding Barangay Geocoded Coordinates...")
b_updated = 0
for b in Barangay.objects.all():
    if b.barangay_name in CARIGARA_BARANGAY_COORDS:
        lat, lng = CARIGARA_BARANGAY_COORDS[b.barangay_name]
    else:
        # Generates realistic Carigara district offsets
        lat = round(base_lat + random.uniform(-0.025, 0.025), 6)
        lng = round(base_lng + random.uniform(-0.030, 0.030), 6)
    b.latitude = lat
    b.longitude = lng
    b.save()
    b_updated += 1

print(f"Updated {b_updated} Barangays with Carigara geocoded coordinates.")

r_updated = 0
for r in EngineeringRecord.objects.all():
    if not r.latitude or not r.longitude:
        b_lat = r.barangay.latitude or base_lat
        b_lng = r.barangay.longitude or base_lng
        # Small micro-offset for specific structure location within barangay
        r.latitude = round(b_lat + random.uniform(-0.003, 0.003), 6)
        r.longitude = round(b_lng + random.uniform(-0.003, 0.003), 6)
        r.save()
        r_updated += 1

print(f"Updated {r_updated} Engineering Records with geocoded structure coordinates.")
