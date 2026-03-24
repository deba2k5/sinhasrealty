import os
import pandas as pd
from pymongo import MongoClient
import certifi

# MongoDB Connection
MONGO_URI = os.getenv("MONGO_URI", 'mongodb+srv://sinhasrealty:sinhasrealty@sinhasrealty.cqt4cec.mongodb.net/?appName=sinhasrealty')
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['sinharealty']

filename = "ORIGINAL TOTAL APARTMENTS AND AVAILIBILITY -with details -6.3.26.xlsx"

print(f"Reading file: {filename}")
xls = pd.ExcelFile(filename, engine='openpyxl')
df = pd.read_excel(xls, sheet_name='OCCUPANCY -Apartment', header=1)
df = df.dropna(subset=['Apartment address'])

counts = {"cities": 0, "buildings": 0, "apartments": 0}

# 1. Process Cities
unique_cities = df['City'].dropna().unique()
city_map = {}
print("Processing Cities...")
for city in unique_cities:
    city_name = str(city).strip()
    city_doc = db.cities.find_one({"city_name_en": city_name})
    if not city_doc:
        result = db.cities.insert_one({
            "city_code": city_name[:2].upper(),
            "city_name_en": city_name,
            "canton": "",
            "country_code": "CH",
            "is_active": True
        })
        city_map[city_name] = result.inserted_id
        counts['cities'] += 1
    else:
        city_map[city_name] = city_doc['_id']

# 2. Process Buildings & Apartments
building_map = {}
print("Processing Buildings and Apartments...")
for idx, row in df.iterrows():
    city_name = str(row['City']).strip() if pd.notna(row['City']) else ""
    if not city_name or city_name not in city_map:
        continue
        
    address = str(row['Apartment address']).strip()
    street_no = str(row['street no']).strip() if pd.notna(row['street no']) else ""
    pin_code = str(row['pin code']).strip() if pd.notna(row['pin code']) else ""
    
    full_address = f"{address} {street_no}, {pin_code} {city_name}".strip()
    
    # Find or create building
    if full_address not in building_map:
        bldg_doc = db.buildings.find_one({"street_address": full_address})
        if not bldg_doc:
            b_id = db.buildings.insert_one({
                "city_id": city_map[city_name],
                "building_code": f"BLDG-{len(building_map)+1000}",
                "street_address": full_address,
                "has_elevator": False,
                "has_parking": False,
                "building_status": "active"
            }).inserted_id
            building_map[full_address] = b_id
            counts['buildings'] += 1
        else:
            building_map[full_address] = bldg_doc['_id']
            
    # Insert apartment if it doesn't already exist
    prop_id = str(row['Property Id']).strip() if pd.notna(row['Property Id']) else f"APT-{idx}"
    apt_doc = db.apartments.find_one({"apt_code": prop_id})
    if not apt_doc:
        try:
            bedrooms = int(float(row['NO. OF ROOMS'])) if pd.notna(row['NO. OF ROOMS']) else 1
        except:
            bedrooms = 1
            
        try:
            sqmt = float(row['Apartment SQMT']) if pd.notna(row['Apartment SQMT']) else 50.0
        except:
            sqmt = 50.0
            
        status_raw = str(row.get('Unnamed: 12', '')).upper()
        status = 'occupied' if 'OCCUPIED' in status_raw else 'available'
        floor = str(row['FLOOR']).strip() if pd.notna(row['FLOOR']) else "0"
        unit = str(row.get(' POSITION', '')).strip() if pd.notna(row.get(' POSITION', '')) else ""
        
        db.apartments.insert_one({
            "building_id": building_map[full_address],
            "apt_code": prop_id,
            "unit_number": unit,
            "floor_number": floor,
            "area_sqm": sqmt,
            "bedrooms": bedrooms,
            "bathrooms": 1,
            "max_occupants": bedrooms * 2,
            "is_ladies_only": False,
            "is_furnished": True,
            "allows_short_term": True,
            "apartment_status": status
        })
        counts['apartments'] += 1

print(f"\nUpload complete!")
print(f"Summary: {counts['cities']} new cities, {counts['buildings']} new buildings, {counts['apartments']} new apartments inserted.")
