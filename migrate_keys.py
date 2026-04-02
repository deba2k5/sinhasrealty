import os
from pymongo import MongoClient
import certifi

# Direct connection to the database to rename keys
MONGO_URI = 'mongodb+srv://sinhasrealty:sinhasrealty@sinhasrealty.cqt4cec.mongodb.net/?appName=sinhasrealty'
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['sinharealty']
collection = db['sinhasrealty data']

# Mapping of old keys (with dots/spaces) to safe keys
rename_map = {
    'INDIV. / SHR.': 'INDIV / SHR',
    ' POSITION': 'POSITION',
    'NO. OF ROOMS': 'NO OF ROOMS',
    'Unnamed: 12': 'Status',
    'WILL SURRENDER BY': 'WILL SURRENDER BY',
    'AWN NO': 'AWN NO',
    'Apartment address': 'Apartment Address',
    'City': 'City',
    'Apartment SQMT': 'Apartment SQMT',
    'pin code': 'Pincode',
    'own/rented': 'Own/Rented',
    'OBJECT NO': 'Object Number',
    'street no': 'Street Number',
    'Property Id': 'Property ID'
}

print("Starting field name migration for 'sinhasrealty data'...")
count = 0
for doc in collection.find():
    new_doc = {}
    changed = False
    for k, v in doc.items():
        if k in rename_map:
            new_doc[rename_map[k]] = v
            changed = True
        elif k.replace('.', '_').replace(' ', '_') != k: # also catch others
            safe_k = k.replace('.', '').strip()
            new_doc[safe_k] = v
            changed = True
        else:
            new_doc[k] = v
    
    if changed:
        # Pymongo 4.0 does not allow dots in keys for insert_one, 
        # but replace_one with the original _id is generally safe.
        collection.replace_one({'_id': doc['_id']}, new_doc)
        count += 1

print(f"Migration complete. Updated {count} documents.")
