from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from bson import ObjectId
import os
import math
import pandas as pd

from dotenv import load_dotenv

# Initialize Flask app
app = Flask(__name__, static_folder='.', static_url_path='')

# MongoDB client setup
load_dotenv()
mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
try:
    import certifi
    mongo_client = MongoClient(mongo_uri, tlsCAFile=certifi.where())
except ImportError:
    mongo_client = MongoClient(mongo_uri)

def get_db():
    return mongo_client['sinhasrealty']


# ─── PAGE ROUTES ──────────────────────────────────────────────────────────────

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/dashboard')
def dashboard_page():
    return send_from_directory('.', 'dashboard.html')

@app.route('/login')
def login_page():
    return send_from_directory('.', 'login.html')

@app.route('/admin')
def admin_page():
    return send_from_directory('.', 'admin.html')

@app.route('/mortgage')
def mortgage_page():
    return send_from_directory('.', 'mortgage_dashboard.html')

@app.route('/mortgage_dashboard')
def mortgage_dashboard_alias():
    return send_from_directory('.', 'mortgage_dashboard.html')


# ─── GUEST CLIENT UPLOAD ──────────────────────────────────────────────────────

@app.route('/upload_guest_client', methods=['POST'])
def upload_guest_client():
    """Upload Guest Client Excel and store parsed sheets into MongoDB."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded.'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected.'}), 400
    try:
        filename = secure_filename(file.filename)
        tmp_dir = os.path.join(os.getcwd(), 'tmp')
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_path = os.path.join(tmp_dir, filename)
        file.save(tmp_path)

        db = get_db()

        # Sheet → collection mapping
        sheet_map = {
            'Guest Profiles': 'guest_profiles',
            'Property Lookup': 'property_lookup',
            'Revenue Tracker': 'revenue_tracker',
        }

        xls = pd.ExcelFile(tmp_path)
        total_inserted = 0
        inserted_per = {}

        for sheet_name, collection_name in sheet_map.items():
            if sheet_name in xls.sheet_names:
                df = pd.read_excel(tmp_path, sheet_name=sheet_name, dtype=str)
                df = df.where(pd.notnull(df), None)  # replace NaN with None
                records = df.to_dict(orient='records')
                if records:
                    db[collection_name].delete_many({})
                    db[collection_name].insert_many(records)
                    inserted_per[collection_name] = len(records)
                    total_inserted += len(records)

        os.remove(tmp_path)

        if total_inserted == 0:
            return jsonify({'success': False, 'message': 'No valid sheets found in the uploaded file.'}), 400

        return jsonify({
            'success': True,
            'message': f'Uploaded {total_inserted} total records.',
            'breakdown': inserted_per
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Upload error: {str(e)}'}), 500


# ─── GUEST CLIENT STATS (for charts + stats cards) ───────────────────────────

@app.route('/api/guest-client-stats', methods=['GET'])
def guest_client_stats():
    """Aggregate stats for all three collections used by the dashboard charts."""
    try:
        db = get_db()

        def group_by(collection, field, limit=20):
            pipeline = [
                {'$match': {field: {'$exists': True, '$ne': None, '$ne': ''}}},
                {'$group': {'_id': f'${field}', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}},
                {'$limit': limit}
            ]
            return list(db[collection].aggregate(pipeline))

        # ── Guest Profiles ──
        gp = db['guest_profiles']
        gp_total = gp.count_documents({})

        # Try common field names for each metric
        guest_type_field = _find_field(gp, ['Guest Type', 'guest_type', 'Type', 'type'])
        vip_field        = _find_field(gp, ['VIP', 'vip', 'VIP Status', 'vip_status'])
        nationality_field= _find_field(gp, ['Nationality', 'nationality', 'Country', 'country'])
        purpose_field    = _find_field(gp, ['Purpose', 'purpose', 'Travel Purpose', 'travel_purpose'])

        # ── Property Lookup ──
        pl = db['property_lookup']
        pl_total = pl.count_documents({})

        status_field    = _find_field(pl, ['Status', 'status', 'Property Status', 'property_status'])
        own_sublet_field= _find_field(pl, ['Own/Sublet', 'own_sublet', 'Type', 'type', 'Own or Sublet'])
        city_field      = _find_field(pl, ['City', 'city', 'Location', 'location'])
        rooms_field     = _find_field(pl, ['Rooms', 'rooms', 'No. of Rooms', 'num_rooms', 'Number of Rooms'])

        # ── Revenue Tracker ──
        rt = db['revenue_tracker']
        rt_total = rt.count_documents({})

        channel_field  = _find_field(rt, ['Booking Channel', 'booking_channel', 'Channel', 'channel'])
        stay_type_field= _find_field(rt, ['Stay Type', 'stay_type', 'Type', 'type'])
        rt_purpose_field=_find_field(rt, ['Purpose of Stay', 'purpose_of_stay', 'Purpose', 'purpose'])
        payment_field  = _find_field(rt, ['Payment Status', 'payment_status', 'Status', 'status'])

        stats = {
            'success': True,
            'guest_profiles': {
                'total': gp_total,
                'guest_types':   group_by('guest_profiles', guest_type_field)  if guest_type_field  else [],
                'vip_types':     group_by('guest_profiles', vip_field)          if vip_field         else [],
                'nationalities': group_by('guest_profiles', nationality_field)  if nationality_field else [],
                'purposes':      group_by('guest_profiles', purpose_field)      if purpose_field     else [],
            },
            'property_lookup': {
                'total': pl_total,
                'statuses':    group_by('property_lookup', status_field)     if status_field     else [],
                'own_sublet':  group_by('property_lookup', own_sublet_field) if own_sublet_field else [],
                'cities':      group_by('property_lookup', city_field, 15)   if city_field       else [],
                'rooms_dist':  group_by('property_lookup', rooms_field)      if rooms_field      else [],
            },
            'revenue_tracker': {
                'total': rt_total,
                'booking_channels':  group_by('revenue_tracker', channel_field)   if channel_field   else [],
                'stay_types':        group_by('revenue_tracker', stay_type_field) if stay_type_field else [],
                'purposes':          group_by('revenue_tracker', rt_purpose_field)if rt_purpose_field else [],
                'payment_statuses':  group_by('revenue_tracker', payment_field)  if payment_field   else [],
            }
        }
        return jsonify(stats)

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


def _find_field(collection, candidates):
    """Return the first candidate field name that exists in at least one document."""
    sample = collection.find_one({})
    if not sample:
        return None
    for c in candidates:
        if c in sample:
            return c
    return None


# ─── GUEST CLIENT COLLECTIONS (paginated data tables) ─────────────────────────

@app.route('/api/guest-client-collections', methods=['GET'])
def guest_client_collections():
    """Return paginated data for a named collection."""
    try:
        collection_name = request.args.get('collection')
        allowed = {'guest_profiles', 'property_lookup', 'revenue_tracker'}
        if not collection_name or collection_name not in allowed:
            return jsonify({'success': False, 'message': f'Invalid or missing collection. Allowed: {allowed}'}), 400

        page  = max(1, int(request.args.get('page', 1)))
        limit = max(1, int(request.args.get('limit', 20)))
        skip  = (page - 1) * limit

        db   = get_db()
        coll = db[collection_name]

        total    = coll.count_documents({})
        records  = list(coll.find({}).skip(skip).limit(limit))

        # Build ordered column list from a sample document
        sample   = coll.find_one({})
        if sample:
            columns = [k for k in sample.keys() if k != '_id']
        else:
            columns = []

        # Stringify ObjectIds
        for doc in records:
            doc['_id'] = str(doc['_id'])

        return jsonify({
            'success':    True,
            'data':       records,
            'total':      total,
            'page':       page,
            'limit':      limit,
            'totalPages': math.ceil(total / limit) if limit else 1,
            'columns':    columns,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ─── GUEST CLIENT UPDATE ──────────────────────────────────────────────────────

@app.route('/api/guest-client-update/<collection>/<record_id>', methods=['POST'])
def guest_client_update(collection, record_id):
    """Update a single document in a guest-client collection."""
    allowed = {'guest_profiles', 'property_lookup', 'revenue_tracker'}
    if collection not in allowed:
        return jsonify({'success': False, 'message': 'Invalid collection.'}), 400
    try:
        data = request.json
        data.pop('_id', None)   # never update _id
        get_db()[collection].update_one(
            {'_id': ObjectId(record_id)},
            {'$set': data}
        )
        return jsonify({'success': True, 'message': 'Record updated.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ─── GUEST CLIENT DELETE ──────────────────────────────────────────────────────

@app.route('/api/guest-client-delete/<collection>/<record_id>', methods=['DELETE'])
def guest_client_delete(collection, record_id):
    """Delete a single document from a guest-client collection."""
    allowed = {'guest_profiles', 'property_lookup', 'revenue_tracker'}
    if collection not in allowed:
        return jsonify({'success': False, 'message': 'Invalid collection.'}), 400
    try:
        result = get_db()[collection].delete_one({'_id': ObjectId(record_id)})
        if result.deleted_count:
            return jsonify({'success': True, 'message': 'Record deleted.'})
        return jsonify({'success': False, 'message': 'Record not found.'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ─── MORTGAGE REGISTER UPLOAD ─────────────────────────────────────────────────

@app.route('/upload_mortgage_register', methods=['POST'])
def upload_mortgage_register():
    """Upload SINHA's mortgage register Excel, process, and store in MongoDB."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded.'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected.'}), 400
    filename = secure_filename(file.filename)
    tmp_dir  = os.path.join(os.getcwd(), 'tmp')
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_path = os.path.join(tmp_dir, filename)
    file.save(tmp_path)
    from mortgage_register_processor import MortgageRegisterProcessor
    processor = MortgageRegisterProcessor(tmp_path)
    records   = processor.process_register()
    os.remove(tmp_path)
    if not records:
        return jsonify({'success': False, 'message': 'No valid rows found in the uploaded file.'}), 400
    db = get_db()
    db['mortgage_register'].delete_many({})
    db['mortgage_register'].insert_many(records)
    return jsonify({'success': True, 'message': f'Inserted {len(records)} mortgage records.', 'records_inserted': len(records)})


# ─── MORTGAGE STATISTICS ──────────────────────────────────────────────────────

@app.route('/api/mortgage/stats', methods=['GET'])
def mortgage_stats():
    coll  = get_db()['mortgage_register']
    total = coll.count_documents({})
    ltv_pipeline = [
        {'$match': {'ltv_percent': {'$exists': True}}},
        {'$bucket': {
            'groupBy': '$ltv_percent',
            'boundaries': [0, 20, 40, 60, 80, 100, 120, 140],
            'default': 'Other',
            'output': {'count': {'$sum': 1}}
        }}
    ]
    ltv_data  = list(coll.aggregate(ltv_pipeline))
    cost_pipeline = [
        {'$match': {'total_acquisition_cost': {'$exists': True}}},
        {'$bucket': {
            'groupBy': '$total_acquisition_cost',
            'boundaries': [0, 50000, 100000, 200000, 300000, 500000, 1000000],
            'default': 'Other',
            'output': {'count': {'$sum': 1}}
        }}
    ]
    cost_data = list(coll.aggregate(cost_pipeline))
    type_pipeline = [
        {'$facet': {
            'initial':    [{'$match': {'refinanced_flag': {'$in': ['No', 'no', 'N', None]}}}, {'$count': 'count'}],
            'refinanced': [{'$match': {'refinanced_flag': {'$regex': 'yes', '$options': 'i'}}}, {'$count': 'count'}]
        }}
    ]
    type_data = list(coll.aggregate(type_pipeline))[0]
    return jsonify({
        'success': True,
        'total': total,
        'ltv_distribution': ltv_data,
        'acquisition_cost_distribution': cost_data,
        'mortgage_type': type_data
    })


# ─── STATIC FILE FALLBACK (must be last) ─────────────────────────────────────

@app.route('/<path:filename>')
def serve_static(filename):
    if os.path.isfile(filename):
        return send_from_directory('.', filename)
    return jsonify({'success': False, 'message': 'Not found'}), 404


@app.errorhandler(404)
def not_found(e):
    return jsonify({'success': False, 'message': 'Page not found'}), 404


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
