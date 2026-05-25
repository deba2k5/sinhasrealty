import requests
import json

# Get data from each collection
collections = ['guest_profiles', 'property_lookup', 'revenue_tracker']

for col in collections:
    r = requests.get(f'http://127.0.0.1:5000/api/data/{col}?limit=5')
    data = r.json()
    if data['data']:
        print(f"\n===== {col.upper()} =====")
        print("Sample record:")
        print(json.dumps(data['data'][0], indent=2, default=str))
        print(f"Total records: {data['total']}")
