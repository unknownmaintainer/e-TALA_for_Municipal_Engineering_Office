import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'etala_project.settings')
django.setup()

from permits.models import Barangay, EngineeringRecord

# Official Master Dataset for the 49 Barangays of Carigara, Leyte, Philippines
# Sources: Philippine Statistics Authority (PSA PSGC 0803715000) & PhilAtlas Reference Centroids
OFFICIAL_49_CARIGARA_BARANGAYS = [
    {"name": "Balilit", "psgc": "0803715001", "lat": 11.2874, "lng": 124.6950},
    {"name": "Barayong", "psgc": "0803715002", "lat": 11.2682, "lng": 124.6722},
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

print("Syncing Official 49 PSA Barangays of Carigara, Leyte...")

valid_names = set()
for item in OFFICIAL_49_CARIGARA_BARANGAYS:
    name = item["name"]
    psgc = item["psgc"]
    lat = item["lat"]
    lng = item["lng"]
    valid_names.add(name.lower())

    # Try matching existing DB entry by name or PSGC
    b = Barangay.objects.filter(barangay_name__iexact=name).first()
    if not b:
        # Check alias without poblacion suffix
        short_name = name.replace(" (Poblacion)", "").strip()
        b = Barangay.objects.filter(barangay_name__iexact=short_name).first()
        
    if not b:
        b = Barangay.objects.create(
            barangay_name=name,
            psgc_code=psgc,
            latitude=lat,
            longitude=lng
        )
        print(f"  [+] Created Barangay: {name} (PSGC: {psgc})")
    else:
        b.barangay_name = name
        b.psgc_code = psgc
        b.latitude = lat
        b.longitude = lng
        b.save()
        print(f"  [✓] Updated Barangay: {name} (PSGC: {psgc})")

# Purge non-official or dummy barangays that are not in official 49 list (e.g. Wang, Barugo)
deleted_count = 0
for b in Barangay.objects.all():
    name_clean = b.barangay_name.lower()
    is_valid = any(name_clean == item["name"].lower() or name_clean == item["name"].replace(" (Poblacion)", "").lower() for item in OFFICIAL_49_CARIGARA_BARANGAYS)
    if not is_valid and b.engineering_records.count() == 0 and b.records.count() == 0:
        print(f"  [-] Removing non-official Barangay: {b.barangay_name}")
        b.delete()
        deleted_count += 1

print(f"\nSUCCESS: Master list synchronized. Total Barangays in DB: {Barangay.objects.count()}. (Purged: {deleted_count})")
