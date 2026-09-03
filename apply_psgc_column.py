import sqlite3
import os
import django

db_path = 'db.sqlite3'
if os.path.exists(db_path):
    print("Checking db.sqlite3 schema for permits_barangay.psgc_code...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(permits_barangay)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'psgc_code' not in columns:
        print("Adding column psgc_code to permits_barangay table...")
        cursor.execute("ALTER TABLE permits_barangay ADD COLUMN psgc_code varchar(20)")
        conn.commit()
        print("Successfully added psgc_code column.")
    else:
        print("Column psgc_code already exists in permits_barangay.")
    conn.close()

# Now setup Django and run seed logic
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'etala_project.settings')
django.setup()

from permits.models import Barangay

OFFICIAL_49_CARIGARA_BARANGAYS = [
    {"name": "Balilit", "psgc": "0803715001", "lat": 11.2874, "lng": 124.6950},
    {"name": "Barayong", "psgc": "0803715002", "lat": 11.2608, "lng": 124.6755},
    {"name": "Barugohay Central", "psgc": "0803715003", "lat": 11.2960, "lng": 124.6986},
    {"name": "Barugohay Norte", "psgc": "0803715004", "lat": 11.3029, "lng": 124.7050},
    {"name": "Barugohay Sur", "psgc": "0803715005", "lat": 11.2720, "lng": 124.6994},
    {"name": "Baybay (Poblacion)", "psgc": "0803715006", "lat": 11.3011, "lng": 124.6889},
    {"name": "Binibihan", "psgc": "0803715007", "lat": 11.2334, "lng": 124.7336},
    {"name": "Bislig", "psgc": "0803715008", "lat": 11.2923, "lng": 124.6769},
    {"name": "Caghalo", "psgc": "0803715009", "lat": 11.2611, "lng": 124.6676},
    {"name": "Camansi", "psgc": "0803715010", "lat": 11.2188, "lng": 124.7159},
    {"name": "Canal", "psgc": "0803715011", "lat": 11.2878, "lng": 124.6826},
    {"name": "Candigahub", "psgc": "0803715012", "lat": 11.2501, "lng": 124.7007},
    {"name": "Canlampay", "psgc": "0803715013", "lat": 11.2649, "lng": 124.6848},
    {"name": "Cogon", "psgc": "0803715014", "lat": 11.2577, "lng": 124.7365},
    {"name": "Cutay", "psgc": "0803715015", "lat": 11.2649, "lng": 124.6987},
    {"name": "East Visoria", "psgc": "0803715016", "lat": 11.3017, "lng": 124.6826},
    {"name": "Guindapunan East", "psgc": "0803715017", "lat": 11.3037, "lng": 124.7004},
    {"name": "Guindapunan West", "psgc": "0803715018", "lat": 11.3026, "lng": 124.6980},
    {"name": "Hiluctogan", "psgc": "0803715019", "lat": 11.2471, "lng": 124.6877},
    {"name": "Jugaban (Poblacion)", "psgc": "0803715020", "lat": 11.3007, "lng": 124.6934},
    {"name": "Libo", "psgc": "0803715021", "lat": 11.2671, "lng": 124.6809},
    {"name": "Lower Hiraan", "psgc": "0803715022", "lat": 11.2795, "lng": 124.6786},
    {"name": "Lower Sogod", "psgc": "0803715023", "lat": 11.2572, "lng": 124.6903},
    {"name": "Macalpi", "psgc": "0803715024", "lat": 11.2126, "lng": 124.7332},
    {"name": "Manloy", "psgc": "0803715025", "lat": 11.2750, "lng": 124.6636},
    {"name": "Nauguisan", "psgc": "0803715026", "lat": 11.2955, "lng": 124.6637},
    {"name": "Pangna", "psgc": "0803715027", "lat": 11.2798, "lng": 124.7101},
    {"name": "Parag-um", "psgc": "0803715028", "lat": 11.2575, "lng": 124.7279},
    {"name": "Parena (Parina)", "psgc": "0803715029", "lat": 11.2979, "lng": 124.7121},
    {"name": "Piloro", "psgc": "0803715030", "lat": 11.2365, "lng": 124.7205},
    {"name": "Ponong (Poblacion)", "psgc": "0803715031", "lat": 11.2977, "lng": 124.6829},
    {"name": "Sagkahan", "psgc": "0803715032", "lat": 11.2799, "lng": 124.7260},
    {"name": "San Mateo (Poblacion)", "psgc": "0803715033", "lat": 11.3018, "lng": 124.6953},
    {"name": "Santa Fe", "psgc": "0803715034", "lat": 11.2567, "lng": 124.7151},
    {"name": "Sawang (Poblacion)", "psgc": "0803715035", "lat": 11.2993, "lng": 124.6895},
    {"name": "Tagak", "psgc": "0803715036", "lat": 11.2891, "lng": 124.7122},
    {"name": "Tangnan", "psgc": "0803715037", "lat": 11.2982, "lng": 124.6713},
    {"name": "Tigbao", "psgc": "0803715038", "lat": 11.2379, "lng": 124.7132},
    {"name": "Tinaguban", "psgc": "0803715039", "lat": 11.2382, "lng": 124.7018},
    {"name": "Upper Hiraan", "psgc": "0803715040", "lat": 11.2648, "lng": 124.6759},
    {"name": "Upper Sogod", "psgc": "0803715041", "lat": 11.2536, "lng": 124.6931},
    {"name": "Uyawan", "psgc": "0803715042", "lat": 11.2841, "lng": 124.6844},
    {"name": "West Visoria", "psgc": "0803715043", "lat": 11.2991, "lng": 124.6769},
    {"name": "Paglaum", "psgc": "0803715044", "lat": 11.2045, "lng": 124.7188},
    {"name": "San Juan", "psgc": "0803715045", "lat": 11.2888, "lng": 124.6611},
    {"name": "Bagong Lipunan", "psgc": "0803715046", "lat": 11.2843, "lng": 124.6987},
    {"name": "Canfabi", "psgc": "0803715047", "lat": 11.2654, "lng": 124.7092},
    {"name": "Rizal (Tagak East)", "psgc": "0803715048", "lat": 11.2867, "lng": 124.7172},
    {"name": "San Isidro", "psgc": "0803715049", "lat": 11.2054, "lng": 124.7082}
]

print("Syncing PSGC data with Django ORM...")
for item in OFFICIAL_49_CARIGARA_BARANGAYS:
    name = item["name"]
    psgc = item["psgc"]
    lat = item["lat"]
    lng = item["lng"]

    b = Barangay.objects.filter(barangay_name__iexact=name).first()
    if not b:
        short_name = name.replace(" (Poblacion)", "").strip()
        b = Barangay.objects.filter(barangay_name__iexact=short_name).first()

    if not b:
        b = Barangay.objects.create(
            barangay_name=name,
            psgc_code=psgc,
            latitude=lat,
            longitude=lng
        )
    else:
        b.barangay_name = name
        b.psgc_code = psgc
        b.latitude = lat
        b.longitude = lng
        b.save()

print("ALL DONE SUCCESSFULLY!")
