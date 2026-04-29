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
                records = [r for r in df.to_dict('records') if any(val for key, val in r.items() if val and str(val).strip())]
                if records:
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
        
        records = [r for r in df.to_dict('records') if any(val for key, val in r.items() if val and str(val).strip())]
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

@app.route('/upload_verwaltung', methods=['POST'])
def handle_upload_verwaltung():
    """Specifically handles the Verwaltung Contacts Excel file with multi-sheet parsing."""
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded."}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No file selected."}), 400
        
    try:
        xls = pd.ExcelFile(file.stream, engine='openpyxl')
        db_inst = get_db()
        
        def clean_val(v):
            if v is None: return None
            if isinstance(v, float) and math.isnan(v): return None
            return str(v).strip()

        # 1. VERWALTUNG CONTACTS sheet
        if "VERWALTUNG CONTACTS" in xls.sheet_names:
            raw = pd.read_excel(xls, sheet_name="VERWALTUNG CONTACTS", header=None)
            col_names = raw.iloc[1].tolist()
            clean_cols = [str(c).replace("\u2192", "->").replace("→", "->").strip() for c in col_names]
            
            df = raw.iloc[2:].copy()
            df.columns = clean_cols
            df = df.dropna(how="all")
            
            rename_map = {
                "Property ID": "PROPERTY_ID",
                "Property Address": "PROPERTY_ADDRESS",
                "OWN / SUB": "OWN_SUB",
                "Agency / Verwaltung Name": "AGENCY_NAME",
                "Agency Address": "AGENCY_ADDRESS",
                "Contact 1 -> Name": "CONTACT1_NAME",
                "Contact 1 -> Mobile": "CONTACT1_MOBILE",
                "Contact 1 -> Landline": "CONTACT1_LANDLINE",
                "Contact 1 -> Email": "CONTACT1_EMAIL",
                "Contact 2 -> Name": "CONTACT2_NAME",
                "Contact 2 -> Mobile": "CONTACT2_MOBILE",
                "Contact 2 -> Landline": "CONTACT2_LANDLINE",
                "Contact 2 -> Email": "CONTACT2_EMAIL",
                "Hauswart -> Name": "HAUSWART_NAME",
                "Hauswart -> Mobile": "HAUSWART_MOBILE",
                "Hauswart -> Landline / Tel": "HAUSWART_LANDLINE",
                "Hauswart -> Email": "HAUSWART_EMAIL",
                "Remarks": "REMARKS",
            }

            
            new_col_map = {}
            for old_col in df.columns:
                matched = False
                for pattern, new_name in rename_map.items():
                    # Robust matching
                    p_norm = "".join(c.lower() for c in pattern if c.isalnum())
                    o_norm = "".join(c.lower() for c in old_col if c.isalnum())
                    if p_norm in o_norm:
                        new_col_map[old_col] = new_name
                        matched = True
                        break

                if not matched: new_col_map[old_col] = old_col

            df = df.rename(columns=new_col_map)
            records = []
            for _, row in df.iterrows():
                rec = {k: clean_val(v) for k, v in row.items()}
                # Skip rows that are effectively empty (no meaningful data)
                if any(val for key, val in rec.items() if val and str(val).strip()):
                    records.append(rec)

            
            if records:
                db_inst["verwaltung_contacts"].delete_many({})
                db_inst["verwaltung_contacts"].insert_many(records)

        # 2. AGENCY SUMMARY sheet
        if "AGENCY SUMMARY" in xls.sheet_names:
            raw2 = pd.read_excel(xls, sheet_name="AGENCY SUMMARY", header=None)
            agency_cols = raw2.iloc[1].tolist()
            df2 = raw2.iloc[2:].copy()
            df2.columns = [str(c).strip() for c in agency_cols]
            df2 = df2.dropna(how="all")
            
            agency_rename = { "#": "RANK", "AGENCY / VERWALTUNG": "AGENCY_NAME", "PROPERTY COUNT": "PROPERTY_COUNT", "PROPERTY IDs": "PROPERTY_IDS" }
            df2 = df2.rename(columns={c: agency_rename.get(c, c) for c in df2.columns})
            
            agency_records = []
            for _, row in df2.iterrows():
                rec = {k: clean_val(v) for k, v in row.items()}
                if rec.get("AGENCY_NAME"): agency_records.append(rec)
                
            if agency_records:
                db_inst["agency_summary"].delete_many({})
                db_inst["agency_summary"].insert_many(agency_records)

        return jsonify({"success": True, "message": "Successfully updated Verwaltung Contacts and Agency Summary collections."})
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"success": False, "message": f"Verwaltung Upload Error: {str(e)}"}), 500


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

        # ─── PHYSICAL ATTRIBUTES STATS ───
        pa_col = get_db()['physical_attributes']
        pa_records = pa_col.count_documents({})
        pa_total = pa_records

        # Count filled vs unfilled records (has BLDG_YEAR_BUILT populated as an indicator)
        pa_filled = pa_col.count_documents({'BLDG_YEAR_BUILT': {"$ne": None}})
        pa_empty  = pa_records - pa_filled

        # Lift availability
        pa_lift_yes = pa_col.count_documents({'LIFT_PRESENT': {"$nin": [None]}})
        pa_lift_no  = pa_records - pa_lift_yes

        # Parking availability
        pa_parking_yes = pa_col.count_documents({'PARKING_AVAILABLE': {"$nin": [None]}})
        pa_parking_no  = pa_records - pa_parking_yes

        # Address coverage (has address)
        pa_has_address = pa_col.count_documents({'ADDRESS': {"$ne": None}})

        # ─── FURNISHINGS & INVENTORY STATS ───
        fi_col = get_db()['furnishings_inventory']
        fi_records = fi_col.count_documents({})
        fi_total = fi_records

        # Check if basic info like bed count is populated
        fi_filled = fi_col.count_documents({'BED_TOTAL_COUNT': {"$ne": None}})
        fi_empty = fi_records - fi_filled

        # TV presence
        fi_tv_yes = fi_col.count_documents({'TV_COUNT': {"$gt": 0}})
        fi_tv_no = fi_records - fi_tv_yes

        # Address coverage
        fi_has_address = fi_col.count_documents({'ADDRESS': {"$ne": None}})

        # Category breakdown by address city (extract city from "Street, Zip City" format)
        pipeline_pa_cities = [
            {"$match": {"ADDRESS": {"$type": "string"}}},
            {"$project": {"city_raw": {"$trim": {"input": {"$arrayElemAt": [{"$split": ["$ADDRESS", ","]}, -1]}}}}},
            {"$project": {"city": {"$trim": {"input": {"$arrayElemAt": [{"$split": ["$city_raw", " "]}, -1]}}}}},
            {"$group": {"_id": "$city", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        pa_cities_data = list(pa_col.aggregate(pipeline_pa_cities))

        pipeline_fi_cities = [
            {"$match": {"ADDRESS": {"$type": "string"}}},
            {"$project": {"city_raw": {"$trim": {"input": {"$arrayElemAt": [{"$split": ["$ADDRESS", ","]}, -1]}}}}},
            {"$project": {"city": {"$trim": {"input": {"$arrayElemAt": [{"$split": ["$city_raw", " "]}, -1]}}}}},
            {"$group": {"_id": "$city", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        fi_cities_data = list(fi_col.aggregate(pipeline_fi_cities))

        vc_col = get_db()['verwaltung_contacts']
        vc_total = vc_col.count_documents({})
        
        vc_has_contact1 = vc_col.count_documents({'CONTACT1_NAME': {"$ne": None}})
        vc_has_hauswart = vc_col.count_documents({'HAUSWART_NAME': {"$ne": None}})
        
        # Additional deep-dive stats for "all details"
        vc_total_mobiles = vc_col.count_documents({
            "$or": [
                {'CONTACT1_MOBILE': {"$ne": None}},
                {'CONTACT2_MOBILE': {"$ne": None}},
                {'HAUSWART_MOBILE': {"$ne": None}}
            ]
        })
        vc_total_emails = vc_col.count_documents({
            "$or": [
                {'CONTACT1_EMAIL': {"$ne": None}},
                {'CONTACT2_EMAIL': {"$ne": None}},
                {'HAUSWART_EMAIL': {"$ne": None}}
            ]
        })
        vc_total_landlines = vc_col.count_documents({
            "$or": [
                {'CONTACT1_LANDLINE': {"$ne": None}},
                {'CONTACT2_LANDLINE': {"$ne": None}},
                {'HAUSWART_LANDLINE': {"$ne": None}}
            ]
        })
        
        as_col = get_db()['agency_summary']
        as_data = list(as_col.find({"AGENCY_NAME": {"$ne": None}}).sort("PROPERTY_COUNT", -1).limit(10))


        return jsonify({
            "success": True,
            "stats": {
                "total": sinhas_total,
                "occupied": sinhas_occupied,
                "available": sinhas_available,
                "partially": sinhas_partially,
                "maintenance": sinhas_maintenance,
                "pa_total": pa_total,
                "pa_records": pa_records,
                "fi_total": fi_total,
                "fi_records": fi_records,
                "vc_total": vc_total,
                "vc_total_mobiles": vc_total_mobiles,
                "vc_total_emails": vc_total_emails,
                "vc_total_landlines": vc_total_landlines,
                "vc_has_contact1": vc_has_contact1,
                "vc_has_hauswart": vc_has_hauswart
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
                "cantons": [{"label": safe_str(cn['_id']), "value": cn['count']} for cn in cantons_data if safe_str(cn['_id'])],
                "pa_fill_rate": [
                    {"label": "Attributes Filled", "value": pa_filled},
                    {"label": "Pending Entry", "value": pa_empty}
                ],
                "pa_address_coverage": [
                    {"label": "Has Address", "value": pa_has_address},
                    {"label": "Missing Address", "value": pa_records - pa_has_address}
                ],
                "pa_cities": [{"label": safe_str(pc['_id']), "value": pc['count']} for pc in pa_cities_data if safe_str(pc['_id'])],
                "fi_fill_rate": [
                    {"label": "Attributes Filled", "value": fi_filled},
                    {"label": "Pending Entry", "value": fi_empty}
                ],
                "fi_address_coverage": [
                    {"label": "Has Address", "value": fi_has_address},
                    {"label": "Missing Address", "value": fi_records - fi_has_address}
                ],
                "fi_tv_presence": [
                    {"label": "Has TV", "value": fi_tv_yes},
                    {"label": "No TV", "value": fi_tv_no}
                ],
                "fi_cities": [{"label": safe_str(fc['_id']), "value": fc['count']} for fc in fi_cities_data if safe_str(fc['_id'])],
                "vc_contact1_coverage": [
                    {"label": "Has Contact 1", "value": vc_has_contact1},
                    {"label": "Missing Contact 1", "value": vc_total - vc_has_contact1}
                ],
                "vc_hauswart_coverage": [
                    {"label": "Has Hauswart", "value": vc_has_hauswart},
                    {"label": "Missing Hauswart", "value": vc_total - vc_has_hauswart}
                ],
                "vc_agencies": [{"label": safe_str(a['AGENCY_NAME']), "value": a['PROPERTY_COUNT']} for a in as_data if safe_str(a['AGENCY_NAME'])]
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
        # Filter out system collections and schema collections
        collections = [c for c in collections if not c.startswith('system.') and not c.endswith('_schema')]
        return jsonify({'success': True, 'collections': collections})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/schema/<collection>', methods=['GET'])
def get_schema(collection):
    try:
        schema_col = get_db()[f"{collection}_schema"]
        schema_docs = list(schema_col.find({}, {'_id': 0}).sort("col_index", 1))
        return jsonify({'success': True, 'schema': schema_docs})
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
