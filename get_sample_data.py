import requests
import json

# Get more records to find ones with data
for col in ['guest_profiles', 'property_lookup', 'revenue_tracker']:
    r = requests.get(f'http://127.0.0.1:5000/api/data/{col}?limit=100&page=2')
    data = r.json()
    
    print(f"\n===== {col.upper()} =====")
    # Find a record with actual data
    for record in data['data']:
        values = [v for k, v in record.items() if k != '_id' and v]
        if values:
            print("Sample with data:")
            print(json.dumps(record, indent=2, default=str)[:800])
            print("...")
            break
