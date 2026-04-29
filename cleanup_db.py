import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "sinharealty")

def cleanup():
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    
    # List of collections to check
    collections = [
        "verwaltung_contacts",
        "property details data",
        "furnishings_inventory",
        "agency_summary"
    ]
    
    for col_name in collections:
        col = db[col_name]
        print(f"Cleaning {col_name}...")
        
        # We need a list of all possible keys to check
        sample = col.find_one()
        if not sample:
            print(f"  -> {col_name} is empty, skipping.")
            continue
            
        fields = [k for k in sample.keys() if k != "_id"]
        
        # MongoDB query to find documents where all specified fields are either null or empty string
        empty_query = {
            "$and": [
                {field: {"$in": [None, ""]}} for field in fields
            ]
        }
        
        result = col.delete_many(empty_query)
        print(f"  -> Deleted {result.deleted_count} empty rows.")

if __name__ == "__main__":
    cleanup()
