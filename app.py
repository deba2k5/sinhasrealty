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
from urllib.parse import unquote
from dotenv import load_dotenv

# Load connection string from .env
load_dotenv()

app = Flask(__name__, static_folder=".")

# ==========================================
# CONFIGURATION
# ==========================================
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://sinhasrealty:sinhasrealty@sinhasrealty.cqt4cec.mongodb.net/?appName=sinhasrealty")

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
        # Standardize column names to be MongoDB safe (remove dots, trim spaces)
        def clean_headers(df):
            new_cols = {}
            for col in df.columns:
                clean_col = str(col).replace('.', '').strip()
                new_cols[col] = clean_col
            return df.rename(columns=new_cols)

        # Replace NaN with None (null) for MongoDB compatibility
        def clean_data(df):
            return df.where(pd.notnull(df), None)

        sheets_inserted = {}
        for sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet)
            df = df.dropna(how='all')
            if not df.empty:
                df = clean_headers(df)
                df = clean_data(df)
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
        xls = pd.ExcelFile(file.stream, engine='openpyxl')
        sheet_name = 'Sheet 1' if 'Sheet 1' in xls.sheet_names else xls.sheet_names[0]
        
        df = pd.read_excel(xls, sheet_name=sheet_name, header=1)
        # Clean headers specifically for MongoDB compatibility
        df.columns = [str(c).replace('.', '').strip() for c in df.columns]
        
        # Filter out empty rows
        df = df.dropna(how='all')
        # Replace NaN with None
        df = df.where(pd.notnull(df), None)
        
        records = df.to_dict('records')
        if records:
            # Clear old data before "populating" with new data
            get_db()['property details data'].delete_many({})
            get_db()['property details data'].insert_many(records)
            
        return jsonify({
            "success": True, 
            "message": f"Success! Uploaded {len(records)} records directly into 'property details data'."
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
    """Manually insert a single record into the 'property details data' collection"""
    data = request.json
    try:
        get_db()['property details data'].insert_one(data)
        addr = data.get('Apartment address', 'record')
        city = data.get('City', '')
        return jsonify({"success": True, "message": f"Successfully added property '{addr}' in {city}."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/download_csv', methods=['GET'])
def download_csv():
    collection_name = request.args.get('collection', 'property details data')
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

@app.route('/api/export-excel', methods=['GET'])
def export_excel():
    """Exports the entire property details collection to a real Excel (.xlsx) file."""
    collection_name = request.args.get('collection', 'property details data')
    try:
        cursor = get_db()[collection_name].find({})
        docs = list(cursor)
        if not docs:
            return "No data found for collection.", 404
            
        # Convert to DataFrame
        df = pd.DataFrame(docs)
        if '_id' in df.columns:
            df.drop(columns=['_id'], inplace=True)
            
        # Output to BytesIO as Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Data Export')
        
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment;filename={collection_name.replace(' ', '_')}_export.xlsx"}
        )
    except Exception as e:
        return f"Error exporting Excel: {str(e)}", 500

@app.route('/admin')
def admin():
    # Serves the Admin HTML frontend
    return send_from_directory('.', 'admin.html')

@app.route('/api/data/<path:collection>', methods=['GET'])
def get_data(collection):
    collection = unquote(collection)  # Fix Vercel not decoding %20 in path params
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        search = request.args.get('search', '').strip()
        f_col = request.args.get('f_col', '').strip()
        f_val = request.args.get('f_val', '').strip()
        sort_field = request.args.get('sort', '_id')
        sort_order = int(request.args.get('order', -1)) # Default to descending (newest)
        skip = (page - 1) * limit

        query = {}

        # 1. Broad Search Clause (Across all string/int fields)
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
                            try:
                                if '.' in search: or_clauses.append({key: float(search)})
                                else: or_clauses.append({key: int(search)})
                            except: pass
                if or_clauses:
                    query = {'$or': or_clauses}

        # 2. Precision Column Filter (Overrides or ANDs with search)
        if f_col and f_val:
            # Use case-insensitive regex for robustness against Title/Upper case labels
            filter_clause = {f_col: {"$regex": f"^{f_val}$", "$options": "i"}}
            if query:
                # If we have a general search, we AND it with the column filter
                query = {"$and": [query, filter_clause]}
            else:
                query = filter_clause

        db_inst = get_db()
        cursor = db_inst[collection].find(query).sort(sort_field, sort_order)
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
            'totalPages': math.ceil(total / limit) if limit > 0 else 1,
            '_col': collection,          # debug: what Flask received
            '_col_repr': repr(collection)  # debug: show exact bytes
        })
    except Exception as e:
        return jsonify({'data': [], 'total': 0, 'page': 1, 'limit': 10, 'totalPages': 0, 'error': str(e), '_col': collection}), 200

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


@app.route('/api/update/<path:collection>/<doc_id>', methods=['POST'])
def update_data(collection, doc_id):
    collection = unquote(collection)  # Fix Vercel URL encoding
    try:
        data = request.json
        if '_id' in data:
            del data['_id']
            
        # Use fetch-merge-replace to allow field names with dots/special characters
        existing = get_db()[collection].find_one({'_id': ObjectId(doc_id)})
        if not existing:
            return jsonify({'success': False, 'message': 'Record not found.'}), 404
            
        existing.update(data)
        # Ensure _id is handled correctly (pymongo insert/replace will error if _id is in the doc and different, 
        # but here it's the same so it's fine, or we can ensure it's removed if needed)
        # but ObjectId is fine.
        result = get_db()[collection].replace_one({'_id': ObjectId(doc_id)}, existing)
        
        if result.modified_count > 0:
            return jsonify({'success': True, 'message': 'Record updated successfully.'})
        return jsonify({'success': True, 'message': 'No changes were made.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/create/<path:collection>', methods=['POST'])
def create_data(collection):
    collection = unquote(collection)  # Fix Vercel URL encoding
    try:
        data = request.json
        if '_id' in data:
            del data['_id']
            
        result = get_db()[collection].insert_one(data)
        
        if result.inserted_id:
            return jsonify({'success': True, 'message': 'Record created successfully.', 'id': str(result.inserted_id)})
        return jsonify({'success': False, 'message': 'Failed to create record.'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        import math
        def safe_str(v):
            """Convert value to string safely, treating NaN/None as empty."""
            if v is None:
                return None
            try:
                if isinstance(v, float) and math.isnan(v):
                    return None
            except Exception:
                pass
            return str(v)

        # Core collection
        sinhas_col = get_db()['property details data']
        
        # ─── DASHBOARD STATS ───
        # Filter: Exclude "SURRENDERED" from total counts and graphs
        status_field = 'OCCUPIED/VACANT/PARTIALLY OCCUPIED/MAINTENANCE'
        filter_query = {status_field: {"$ne": "SURRENDERED"}}

        sinhas_total = sinhas_col.count_documents(filter_query)
        sinhas_occupied = sinhas_col.count_documents({status_field: "OCCUPIED"})
        sinhas_available = sinhas_col.count_documents({status_field: "VACANT"})
        sinhas_partially = sinhas_col.count_documents({status_field: "PARTIALLY OCCUPIED"})
        sinhas_maintenance = sinhas_col.count_documents({status_field: "MAINTENANCE"})

        # Group by Property Type
        type_field = 'PROPERTY TYPE-APARTMENT/HOUSE/CHALET/OFFICE/PARKING/GARAGE'
        pipeline_types = [
            {"$match": filter_query},
            {"$group": {"_id": f"${type_field}", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        types_data = list(sinhas_col.aggregate(pipeline_types))

        # City Distribution
        pipeline_cities = [
            {"$match": {"CITY": {"$exists": True, "$type": "string"}}},
            {"$group": {"_id": "$CITY", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        cities_data = list(sinhas_col.aggregate(pipeline_cities))

        # Class Distribution
        class_field = 'PROPERTY CLASS (A/B/C)'
        pipeline_class = [
            {"$match": filter_query},
            {"$group": {"_id": f"${class_field}", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        class_data = list(sinhas_col.aggregate(pipeline_class))

        # OTA Distribution
        ota_field = 'OTA/NON OTA'
        pipeline_ota = [
            {"$match": {ota_field: {"$exists": True, "$type": "string"}}},
            {"$group": {"_id": f"${ota_field}", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        ota_data = list(sinhas_col.aggregate(pipeline_ota))

        # Canton Distribution
        pipeline_cantons = [
            {"$match": {"CANTON": {"$exists": True, "$type": "string"}}},
            {"$group": {"_id": "$CANTON", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        cantons_data = list(sinhas_col.aggregate(pipeline_cantons))

        return jsonify({
            "success": True,
            "stats": {
                "total": sinhas_total,
                "occupied": sinhas_occupied,
                "available": sinhas_available,
                "partially": sinhas_partially,
                "maintenance": sinhas_maintenance
            },
            "charts": {
                "occupancy": [
                    {"label": "Occupied", "value": sinhas_occupied},
                    {"label": "Vacant", "value": sinhas_available},
                    {"label": "Partially Occupied", "value": sinhas_partially},
                    {"label": "Maintenance", "value": sinhas_maintenance}
                ],
                "types": [{"label": safe_str(t['_id']), "value": t['count']} for t in types_data if safe_str(t['_id'])],
                "cities": [{"label": safe_str(c['_id']), "value": c['count']} for c in cities_data if safe_str(c['_id'])],
                "classes": [{"label": safe_str(cl['_id']), "value": cl['count']} for cl in class_data if safe_str(cl['_id'])],
                "otas": [{"label": safe_str(o['_id']), "value": o['count']} for o in ota_data if safe_str(o['_id'])],
                "cantons": [{"label": safe_str(cn['_id']), "value": cn['count']} for cn in cantons_data if safe_str(cn['_id'])]
            }
        })
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'message': str(e), 'trace': traceback.format_exc()}), 500

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
    print(f" Sinha's GmbH Portal Backend Started ")
    print(f"=====================================")
    print(f" Connected DB: {MONGO_URI}")
    print(f" Dashboard is live at: http://localhost:5000")
    # Run the server on port 5000
    app.run(port=5000, debug=True)
