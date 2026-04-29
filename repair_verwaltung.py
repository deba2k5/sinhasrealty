import os
import math
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "sinharealty")


def repair():
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    col = db["verwaltung_contacts"]
    
    rename_map = {
        "Property ID":               "PROPERTY_ID",
        "Property Address":          "PROPERTY_ADDRESS",
        "OWN / SUB":                 "OWN_SUB",
        "Agency / Verwaltung Name":  "AGENCY_NAME",
        "Agency Address":            "AGENCY_ADDRESS",
        "Contact 1 -> Name":         "CONTACT1_NAME",
        "Contact 1 -> Mobile":       "CONTACT1_MOBILE",
        "Contact 1 -> Landline":     "CONTACT1_LANDLINE",
        "Contact 1 -> Email":        "CONTACT1_EMAIL",
        "Contact 2 -> Name":         "CONTACT2_NAME",
        "Contact 2 -> Mobile":       "CONTACT2_MOBILE",
        "Contact 2 -> Landline":     "CONTACT2_LANDLINE",
        "Contact 2 -> Email":        "CONTACT2_EMAIL",
        "Hauswart -> Name":          "HAUSWART_NAME",
        "Hauswart -> Mobile":        "HAUSWART_MOBILE",
        "Hauswart -> Landline / Tel":"HAUSWART_LANDLINE",
        "Hauswart -> Email":         "HAUSWART_EMAIL",
        "Remarks":                   "REMARKS",
    }
    
    print(f"Repairing collection: {col.name} in DB: {MONGO_DB}...")
    
    docs = list(col.find())
    repaired_count = 0
    
    for doc in docs:
        doc_id = doc.get("_id")
        updates = {}
        keys_to_remove = []
        
        for old_key, val in doc.items():
            if old_key == "_id": continue
            
            # Find if this key matches any of our patterns
            matched_new_key = None
            o_norm = "".join(c.lower() for c in str(old_key) if c.isalnum())
            
            for pattern, new_name in rename_map.items():
                p_norm = "".join(c.lower() for c in pattern if c.isalnum())
                if p_norm == o_norm or (p_norm in o_norm and len(p_norm) > 10):
                    matched_new_key = new_name
                    break
            
            if matched_new_key and matched_new_key != old_key:
                updates[matched_new_key] = val
                keys_to_remove.append(old_key)
        
        if updates:
            # Perform update
            col.update_one({"_id": doc_id}, {
                "$set": updates,
                "$unset": {k: "" for k in keys_to_remove}
            })
            repaired_count += 1
            
    print(f"Finished! Repaired {repaired_count} documents.")

if __name__ == "__main__":
    repair()
