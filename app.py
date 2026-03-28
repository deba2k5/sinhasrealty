import os
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory, Response
from pymongo import MongoClient
import certifi
import io
import csv
from bson.objectid import ObjectId
import math
import re

app = Flask(__name__, static_folder=".")

# ==========================================
# CONFIGURATION
# ==========================================
MONGO_URI = os.getenv("MONGO_URI", 'mongodb+srv://sinhasrealty:sinhasrealty@sinhasrealty.cqt4cec.mongodb.net/?appName=sinhasrealty')

# Lazy MongoDB connection — avoids crash-on-import during Render build
_client = None
_db = None

def get_db():
    global _client, _db
    if _db is None:
        _client = MongoClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
        _db = _client['sinharealty']
    return _db

@app.route('/login')
def login():
    return send_from_directory('.', 'login.html')

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
                get_db()[collection_name].insert_many(records)
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
                get_db()[sheet].insert_many(records)
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
            city_doc = get_db().cities.find_one({"city_name_en": city_name})
            if not city_doc:
                result = get_db().cities.insert_one({
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
                bldg_doc = get_db().buildings.find_one({"street_address": full_address})
                if not bldg_doc:
                    b_id = get_db().buildings.insert_one({
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
            apt_doc = get_db().apartments.find_one({"apt_code": prop_id})
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
                
                get_db().apartments.insert_one({
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
        get_db().cities.insert_one(data)
        return jsonify({"success": True, "message": f"Successfully added city: {data.get('city_name')}"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/add_property', methods=['POST'])
def add_property():
    """Manually insert a single record into the 'sinhasrealty data' collection"""
    data = request.json
    try:
        get_db()['sinhasrealty data'].insert_one(data)
        addr = data.get('Apartment address', 'record')
        city = data.get('City', '')
        return jsonify({"success": True, "message": f"Successfully added property '{addr}' in {city}."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/download_csv', methods=['GET'])
def download_csv():
    collection_name = request.args.get('collection', 'sinhasrealty data')
    try:
        cursor = get_db()[collection_name].find({})
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
@app.route('/admin')
def admin():
    # Serves the Admin HTML frontend
    return send_from_directory('.', 'admin.html')

@app.route('/api/data/<collection>', methods=['GET'])
def get_data(collection):
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        search = request.args.get('search', '').strip()
        skip = (page - 1) * limit

        query = {}

        if search:
            regex = re.compile(search, re.IGNORECASE)
            sample = get_db()[collection].find_one()
            if sample:
                or_clauses = []
                for key, val in sample.items():
                    if key != '_id':
                        if isinstance(val, str):
                            or_clauses.append({key: {"$regex": regex}})
                        elif isinstance(val, (int, float)) and search.replace('.', '', 1).isdigit():
                            if '.' in search:
                                or_clauses.append({key: float(search)})
                            else:
                                or_clauses.append({key: int(search)})
                if or_clauses:
                    query = {'$or': or_clauses}

        db_inst = get_db()
        cursor = db_inst[collection].find(query)
        total = db_inst[collection].count_documents(query)

        docs = list(cursor.skip(skip).limit(limit))
        for doc in docs:
            doc['_id'] = str(doc['_id'])
            for k, v in doc.items():
                if isinstance(v, ObjectId):
                    doc[k] = str(v)
                elif isinstance(v, float) and math.isnan(v):
                    doc[k] = None

        return jsonify({
            'data': docs,
            'total': total,
            'page': page,
            'limit': limit,
            'totalPages': math.ceil(total / limit) if limit > 0 else 1
        })
    except Exception as e:
        return jsonify({'data': [], 'total': 0, 'page': 1, 'limit': 10, 'totalPages': 0, 'error': str(e)}), 200

@app.route('/api/debug', methods=['GET'])
def debug_connection():
    """Debug endpoint to check MongoDB connectivity and collection state on Vercel"""
    try:
        db_inst = get_db()
        collections = db_inst.list_collection_names()
        counts = {}
        for col in collections:
            try:
                counts[col] = db_inst[col].count_documents({})
            except Exception as ce:
                counts[col] = f"ERROR: {ce}"
        return jsonify({
            'success': True,
            'mongo_uri_set': bool(os.getenv('MONGO_URI')),
            'collections': collections,
            'counts': counts
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'mongo_uri_set': bool(os.getenv('MONGO_URI'))}), 500


@app.route('/api/update/<collection>/<doc_id>', methods=['POST'])
def update_data(collection, doc_id):
    try:
        data = request.json
        if '_id' in data:
            del data['_id']
            
        # Optional: Handle strings that might actually be ObjectId references (like city_id, building_id)
        # Here we do a simple generic update
        result = get_db()[collection].update_one({'_id': ObjectId(doc_id)}, {'$set': data})
        
        if result.modified_count > 0:
            return jsonify({'success': True, 'message': 'Record updated successfully.'})
        return jsonify({'success': True, 'message': 'No changes were made.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        total_apartments = get_db().apartments.count_documents({})
        occupied_apartments = get_db().apartments.count_documents({'apartment_status': 'occupied'})
        available_apartments = get_db().apartments.count_documents({'apartment_status': 'available'})
        
        total_buildings = get_db().buildings.count_documents({})
        total_cities = get_db().cities.count_documents({})
        
        # Specific stats for sinhasrealty data
        sinhas_total = get_db()['sinhasrealty data'].count_documents({})
        sinhas_occupied = get_db()['sinhasrealty data'].count_documents({'Unnamed: 12': {'$regex': 'OCCUPIED', '$options': 'i'}})
        sinhas_available = sinhas_total - sinhas_occupied
        
        pipeline = [
            {"$group": {"_id": "$City", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        city_stats = list(get_db()['sinhasrealty data'].aggregate(pipeline))
        sinhas_cities = {str(item['_id']): item['count'] for item in city_stats if item['_id']}
        
        return jsonify({
            'success': True,
            'apartments': {
                'total': total_apartments,
                'occupied': occupied_apartments,
                'available': available_apartments
            },
            'buildings': total_buildings,
            'cities': total_cities,
            'sinhasrealty_data': {
                'total': sinhas_total,
                'occupied': sinhas_occupied,
                'available': sinhas_available,
                'city_distribution': sinhas_cities
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/collections', methods=['GET'])
def get_collections():
    try:
        # Get all collection names, filtering out system collections if necessary
        collections = get_db().list_collection_names()
        # Filter out system collections if any
        collections = [c for c in collections if not c.startswith('system.')]
        return jsonify({'success': True, 'collections': collections})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    print(f"=====================================")
    print(f" Sinha Realty Portal Backend Started ")
    print(f"=====================================")
    print(f" Connected DB: {MONGO_URI}")
    print(f" Dashboard is live at: http://localhost:5000")
    # Run the server on port 5000
    app.run(port=5000, debug=True)
