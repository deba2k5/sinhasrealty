# ============================================
# MORTGAGE REGISTER ENDPOINTS
# ============================================

@app.route('/upload_mortgage_register', methods=['POST'])
def upload_mortgage_register():
    """Upload Own Property Purchase & Mortgage Register from Excel"""
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded."}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No file selected."}), 400
        
    try:
        from mortgage_register_processor import MortgageRegisterProcessor
        import tempfile
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        # Process the file
        processor = MortgageRegisterProcessor(tmp_path)
        records = processor.process_register()
        
        if records:
            # Clear existing and insert new
            db_inst = get_db()
            db_inst['mortgage_register'].delete_many({})
            result = db_inst['mortgage_register'].insert_many(records)
            
            # Clean up
            os.remove(tmp_path)
            
            return jsonify({
                "success": True,
                "message": f"Success! Uploaded {len(records)} properties to mortgage_register",
                "count": len(records)
            })
        else:
            os.remove(tmp_path)
            return jsonify({"success": False, "message": "No valid property records found"}), 400
            
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"success": False, "message": f"Upload Error: {str(e)}"}), 500

@app.route('/api/mortgage-register', methods=['GET'])
def get_mortgage_register():
    """Get mortgage register with filtering, sorting, and pagination"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        sort_field = request.args.get('sort', 'property_id')
        sort_order = int(request.args.get('order', 1))
        search = request.args.get('search', '').strip()
        city_filter = request.args.get('city', '').strip()
        canton_filter = request.args.get('canton', '').strip()
        bank_filter = request.args.get('bank', '').strip()
        financing_type_filter = request.args.get('financing_type', '').strip()
        
        skip = (page - 1) * limit
        
        db_inst = get_db()
        col = db_inst['mortgage_register']
        
        # Build query
        query = {}
        
        # Search across text fields
        if search:
            regex = re.compile(search, re.IGNORECASE)
            query['$or'] = [
                {'property_id': {'$regex': regex}},
                {'property_name': {'$regex': regex}},
                {'address': {'$regex': regex}}
            ]
        
        # Filters
        if city_filter:
            query['address'] = {'$regex': city_filter, '$options': 'i'}
        if canton_filter:
            if 'address' in query and isinstance(query['address'], dict):
                query['$and'] = [{'address': query.pop('address')}, {'address': {'$regex': canton_filter, '$options': 'i'}}]
            else:
                query['address'] = {'$regex': canton_filter, '$options': 'i'}
        if bank_filter:
            query['$or'] = query.get('$or', [])
            query['$or'].extend([
                {'initial_bank': {'$regex': bank_filter, '$options': 'i'}},
                {'refinancing_bank': {'$regex': bank_filter, '$options': 'i'}}
            ])
        if financing_type_filter:
            query['initial_financing_type'] = financing_type_filter
        
        # Get total and records
        total = col.count_documents(query)
        cursor = col.find(query).sort(sort_field, sort_order).skip(skip).limit(limit)
        records = list(cursor)
        
        # Convert ObjectId to string
        for doc in records:
            doc['_id'] = str(doc['_id'])
        
        return jsonify({
            'success': True,
            'data': records,
            'total': total,
            'page': page,
            'limit': limit,
            'totalPages': math.ceil(total / limit) if limit > 0 else 1
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/mortgage-register/<doc_id>', methods=['GET'])
def get_mortgage_record(doc_id):
    """Get a single mortgage register record"""
    try:
        record = get_db()['mortgage_register'].find_one({'_id': ObjectId(doc_id)})
        if not record:
            return jsonify({'success': False, 'message': 'Record not found'}), 404
        
        record['_id'] = str(record['_id'])
        return jsonify({'success': True, 'data': record})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/mortgage-register/<doc_id>', methods=['POST'])
def update_mortgage_record(doc_id):
    """Update a mortgage register record"""
    try:
        data = request.json
        if '_id' in data:
            del data['_id']
        
        data['updated_at'] = datetime.datetime.now().isoformat()
        
        # Recalculate KPIs
        from mortgage_register_processor import MortgageRegisterProcessor
        processor = MortgageRegisterProcessor('')
        
        existing = get_db()['mortgage_register'].find_one({'_id': ObjectId(doc_id)})
        if not existing:
            return jsonify({'success': False, 'message': 'Record not found'}), 404
        
        existing.update(data)
        existing = processor.calculate_kpis(existing)
        
        result = get_db()['mortgage_register'].replace_one({'_id': ObjectId(doc_id)}, existing)
        
        if result.modified_count > 0 or result.matched_count > 0:
            return jsonify({'success': True, 'message': 'Record updated successfully.'})
        return jsonify({'success': True, 'message': 'No changes made.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/mortgage-register', methods=['POST'])
def create_mortgage_record():
    """Create a new mortgage register record"""
    try:
        data = request.json
        if '_id' in data:
            del data['_id']
        
        data['record_type'] = 'own_property_mortgage_register'
        data['created_at'] = datetime.datetime.now().isoformat()
        data['updated_at'] = datetime.datetime.now().isoformat()
        
        # Calculate KPIs
        from mortgage_register_processor import MortgageRegisterProcessor
        processor = MortgageRegisterProcessor('')
        data = processor.calculate_kpis(data)
        
        result = get_db()['mortgage_register'].insert_one(data)
        
        return jsonify({
            'success': True,
            'message': 'Record created successfully.',
            'id': str(result.inserted_id)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/mortgage-register/<doc_id>', methods=['DELETE'])
def delete_mortgage_record(doc_id):
    """Delete a mortgage register record"""
    try:
        result = get_db()['mortgage_register'].delete_one({'_id': ObjectId(doc_id)})
        
        if result.deleted_count > 0:
            return jsonify({'success': True, 'message': 'Record deleted successfully.'})
        return jsonify({'success': False, 'message': 'Record not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/mortgage-analytics', methods=['GET'])
def get_mortgage_analytics():
    """Get portfolio analytics and KPIs"""
    try:
        col = get_db()['mortgage_register']
        
        # Portfolio Summary
        all_records = list(col.find({}))
        
        if not all_records:
            return jsonify({'success': True, 'analytics': {}})
        
        total_acquisition_cost = sum(float(r.get('total_acquisition_cost', 0) or 0) for r in all_records)
        total_equity = sum(float(r.get('own_capital', 0) or 0) for r in all_records)
        total_mortgage = sum(float(r.get('effective_current_mortgage', 0) or 0) for r in all_records)
        total_annual_interest = sum(float(r.get('annual_interest_cost', 0) or 0) for r in all_records)
        
        # Aggregate stats
        avg_ltv = sum(float(r.get('ltv_percent', 0) or 0) for r in all_records) / len(all_records) if all_records else 0
        avg_equity_pct = (total_equity / total_acquisition_cost * 100) if total_acquisition_cost > 0 else 0
        portfolio_ltv = (total_mortgage / total_acquisition_cost * 100) if total_acquisition_cost > 0 else 0
        
        # By Bank
        bank_summary = {}
        for rec in all_records:
            bank = rec.get('initial_bank') or 'Unknown'
            if bank not in bank_summary:
                bank_summary[bank] = {
                    'count': 0,
                    'total_mortgage': 0,
                    'total_interest': 0
                }
            bank_summary[bank]['count'] += 1
            bank_summary[bank]['total_mortgage'] += float(rec.get('effective_current_mortgage', 0) or 0)
            bank_summary[bank]['total_interest'] += float(rec.get('annual_interest_cost', 0) or 0)
        
        # By Financing Type
        financing_type_summary = {}
        for rec in all_records:
            ftype = rec.get('initial_financing_type') or 'Unknown'
            if ftype not in financing_type_summary:
                financing_type_summary[ftype] = {
                    'count': 0,
                    'total_mortgage': 0,
                    'avg_rate': 0
                }
            financing_type_summary[ftype]['count'] += 1
            financing_type_summary[ftype]['total_mortgage'] += float(rec.get('effective_current_mortgage', 0) or 0)
        
        # Upcoming renewals (within 12 months)
        upcoming_renewals = []
        today = datetime.datetime.now()
        for rec in all_records:
            maturity = rec.get('initial_maturity_date') or rec.get('refinancing_maturity_date')
            if maturity:
                try:
                    mat_date = pd.to_datetime(maturity)
                    if today <= mat_date <= today + datetime.timedelta(days=365):
                        upcoming_renewals.append({
                            'property_id': rec.get('property_id'),
                            'maturity_date': maturity,
                            'days_until_renewal': (mat_date - today).days
                        })
                except:
                    pass
        
        return jsonify({
            'success': True,
            'analytics': {
                'portfolio_summary': {
                    'total_properties': len(all_records),
                    'total_acquisition_cost': round(total_acquisition_cost, 2),
                    'total_equity': round(total_equity, 2),
                    'total_mortgage': round(total_mortgage, 2),
                    'total_annual_interest': round(total_annual_interest, 2),
                    'avg_monthly_interest': round(total_annual_interest / 12, 2),
                    'avg_ltv_percent': round(avg_ltv, 2),
                    'portfolio_ltv_percent': round(portfolio_ltv, 2),
                    'avg_equity_percent': round(avg_equity_pct, 2)
                },
                'by_bank': {k: {
                    'count': v['count'],
                    'total_mortgage': round(v['total_mortgage'], 2),
                    'total_annual_interest': round(v['total_interest'], 2)
                } for k, v in bank_summary.items()},
                'by_financing_type': {k: {
                    'count': v['count'],
                    'total_mortgage': round(v['total_mortgage'], 2)
                } for k, v in financing_type_summary.items()},
                'upcoming_renewals': sorted(upcoming_renewals, key=lambda x: x['days_until_renewal'])[:10]
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
