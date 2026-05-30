from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from pymongo import MongoClient
import os

# Initialize Flask app
app = Flask(__name__, static_folder='.', static_url_path='')

# MongoDB client setup (adjust connection string if needed)
mongo_client = MongoClient('mongodb://localhost:27017/')

def get_db():
    # Replace 'sinhasrealty' with your actual database name if different
    return mongo_client['sinhasrealty']

# Serve main landing page
@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

# Optional static pages
@app.route('/dashboard')
def dashboard_page():
    return send_from_directory('.', 'dashboard.html')

@app.route('/login')
def login_page():
    return send_from_directory('.', 'login.html')

@app.route('/mortgage_dashboard')
def mortgage_dashboard():
    return send_from_directory('.', 'mortgage_dashboard.html')

# Upload mortgage register Excel file
@app.route('/upload_mortgage_register', methods=['POST'])
def upload_mortgage_register():
    """Upload SINHA's mortgage register Excel, process, and store in MongoDB"""
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded."}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No file selected."}), 400
    filename = secure_filename(file.filename)
    tmp_dir = os.path.join(os.getcwd(), 'tmp')
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_path = os.path.join(tmp_dir, filename)
    file.save(tmp_path)
    # Process using existing processor
    from mortgage_register_processor import MortgageRegisterProcessor
    processor = MortgageRegisterProcessor(tmp_path)
    records = processor.process_register()
    os.remove(tmp_path)
    if not records:
        return jsonify({"success": False, "message": "No valid rows found in the uploaded file."}), 400
    db = get_db()
    db['mortgage_register'].delete_many({})
    db['mortgage_register'].insert_many(records)
    return jsonify({"success": True, "message": f"Inserted {len(records)} mortgage records.", "records_inserted": len(records)})

# Mortgage statistics endpoint
@app.route('/api/mortgage/stats', methods=['GET'])
def mortgage_stats():
    coll = get_db()['mortgage_register']
    total = coll.count_documents({})
    # LTV distribution buckets
    ltv_pipeline = [
        {"$match": {"ltv_percent": {"$exists": True}}},
        {"$bucket": {
            "groupBy": "$ltv_percent",
            "boundaries": [0, 20, 40, 60, 80, 100, 120, 140],
            "default": "Other",
            "output": {"count": {"$sum": 1}}
        }}
    ]
    ltv_data = list(coll.aggregate(ltv_pipeline))
    # Acquisition cost histogram (rounded to nearest 50k)
    cost_pipeline = [
        {"$match": {"total_acquisition_cost": {"$exists": True}}},
        {"$bucket": {
            "groupBy": "$total_acquisition_cost",
            "boundaries": [0, 50000, 100000, 200000, 300000, 500000, 1000000],
            "default": "Other",
            "output": {"count": {"$sum": 1}}
        }}
    ]
    cost_data = list(coll.aggregate(cost_pipeline))
    # Mortgage type breakdown
    type_pipeline = [
        {"$facet": {
            "initial": [{"$match": {"refinanced_flag": {"$in": ["No", "no", "N", None]}}}, {"$count": "count"}],
            "refinanced": [{"$match": {"refinanced_flag": {"$regex": "yes", "$options": "i"}}}, {"$count": "count"}]
        }}
    ]
    type_data = list(coll.aggregate(type_pipeline))[0]
    return jsonify({
        "success": True,
        "total": total,
        "ltv_distribution": ltv_data,
        "acquisition_cost_distribution": cost_data,
        "mortgage_type": type_data
    })

# Admin page
@app.route('/admin')
def admin_page():
    return send_from_directory('.', 'admin.html')

# Mortgage page (alias)
@app.route('/mortgage')
def mortgage_page():
    return send_from_directory('.', 'mortgage_dashboard.html')

# Generic static file fallback (placed after specific routes)
@app.route('/<path:filename>')
def serve_static(filename):
    if os.path.isfile(filename):
        return send_from_directory('.', filename)
    else:
        return "File not found", 404

# 404 error handler for unmatched routes
@app.errorhandler(404)
def not_found(e):
    return "Page not found", 404

# For serverless deployments
def handler(event, context):
    return app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
