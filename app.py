import os
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory, Response
from pymongo import MongoClient
import certifi
import io
import csv

app = Flask(__name__, static_folder=".")

# ==========================================
# CONFIGURATION
# Update this with your actual MongoDB connection string
# ==========================================
MONGO_URI = os.getenv("MONGO_URI", 'mongodb+srv://sinhasrealty:sinhasrealty@sinhasrealty.cqt4cec.mongodb.net/?appName=sinhasrealty')
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['sinharealty']

@app.route('/')
def index():
    # Serves the HTML frontend
    return send_from_directory('.', 'index.html')

@app.route('/upload', methods=['POST'])
def handle_upload():
    """Handles parsing and uploading the Excel file to the database"""
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded."}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No file selected."}), 400
        
    try:
        filename = file.filename.lower()
        if filename.endswith('.csv'):
            df = pd.read_csv(file.stream)
            df = df.dropna(how='all')
            collection_name = file.filename.rsplit('.', 1)[0]
            records = df.to_dict('records')
            if records:
                db[collection_name].insert_many(records)
                return jsonify({"success": True, "message": f"Success! {len(records)} rows -> '{collection_name}'"})
            return jsonify({"success": True, "message": "CSV file was empty."})
            
        # If it's an Excel file
        xls = pd.ExcelFile(file.stream, engine='openpyxl')
        sheets_inserted = {}
        
        for sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet)
            df = df.dropna(how='all')
            if not df.empty:
                records = df.to_dict('records')
                db[sheet].insert_many(records)
                sheets_inserted[sheet] = len(records)
                
        msg = ", ".join([f"{count} rows -> '{sheet}'" for sheet, count in sheets_inserted.items()])
        if not sheets_inserted:
            msg = "Empty file, nothing imported."
            
        return jsonify({"success": True, "message": f"Success! {msg}"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Database Error: {str(e)}"}), 500

@app.route('/upload_occupancy', methods=['POST'])
def handle_upload_occupancy():
    """Handles the specific 'TOTAL APARTMENTS' occupancy Excel format and maps it to the new hierarchy."""
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded."}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No file selected."}), 400
        
    try:
        # Read the Excel sheet directly from the memory stream without saving to disk
        xls = pd.ExcelFile(file.stream, engine='openpyxl')
        if 'OCCUPANCY -Apartment' not in xls.sheet_names:
            return jsonify({"success": False, "message": "Missing 'OCCUPANCY -Apartment' sheet."}), 400
            
        df = pd.read_excel(xls, sheet_name='OCCUPANCY -Apartment', header=1)
        # Drop rows where 'Apartment address' is definitely NaN
        df = df.dropna(subset=['Apartment address'])
        
        counts = {"cities": 0, "buildings": 0, "apartments": 0}
        
        # 1. Process Cities
        unique_cities = df['City'].dropna().unique()
        city_map = {}
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
                
        return jsonify({
            "success": True, 
            "message": f"Success! Inserted {counts['cities']} new cities, {counts['buildings']} buildings, and {counts['apartments']} apartments."
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"ETL Error: {str(e)}"}), 500

@app.route('/add_city', methods=['POST'])
def add_city():
    """Manual endpoint example for adding a single city to the cities table"""
    data = request.json
    try:
        db.cities.insert_one(data)
        return jsonify({"success": True, "message": f"Successfully added city: {data.get('city_name')}"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/download_csv', methods=['GET'])
def download_csv():
    collection_name = request.args.get('collection', 'sinhasrealty data')
    try:
        cursor = db[collection_name].find({})
        docs = list(cursor)
        if not docs:
            return "No data found for collection.", 404
            
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Get all unique headers across docs to be safe
        keys_set = set()
        for doc in docs:
            keys_set.update(doc.keys())
        keys = list(keys_set)
        if '_id' in keys: keys.remove('_id')
        
        # Write headers
        writer.writerow(keys)
        
        # Write rows
        for doc in docs:
            writer.writerow([str(doc.get(k, '')) for k in keys])
            
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename={collection_name}_export.csv"}
        )
    except Exception as e:
        return f"Error exporting CSV: {str(e)}", 500

if __name__ == '__main__':
    print(f"=====================================")
    print(f" Sinha Realty Portal Backend Started ")
    print(f"=====================================")
    print(f" Connected DB: {MONGO_URI}")
    print(f" Dashboard is live at: http://localhost:5000")
    # Run the server on port 5000
    app.run(port=5000, debug=True)
