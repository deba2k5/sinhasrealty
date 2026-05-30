import os
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Existing imports from app.py (kept for context) 
# ... (the rest of app.py unchanged up to line 46)

# Add new route for mortgage register upload
@app.route('/upload_mortgage_register', methods=['POST'])
def upload_mortgage_register():
    """Upload SINHAS mortgage register Excel, process, and store in MongoDB"""
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded."}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No file selected."}), 400
    filename = secure_filename(file.filename)
    tmp_dir = os.path.join(os.getcwd(), 'tmp')
    if not os.path.isdir(tmp_dir):
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

# Add stats endpoint for mortgage data
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

# Serve mortgage dashboard page
@app.route('/mortgage_dashboard')
def mortgage_dashboard():
    return send_from_directory('.', 'mortgage_dashboard.html')

def handler(event, context):
    return app
