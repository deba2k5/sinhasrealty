from pymongo import MongoClient
import os
import certifi
from dotenv import load_dotenv

load_dotenv()
mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri, tlsCAFile=certifi.where())
db = client['sinharealty']

target_collections = ['cities', 'apartments', 'buildings', 'sinhasrealty data', 'apartment details data', 'property details data']
for col in target_collections:
    db.drop_collection(col)
    print(f"Dropped '{col}' in 'sinharealty' database.")

print("Cleanup of 'sinharealty' database complete.")
