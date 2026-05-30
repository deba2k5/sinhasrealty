import os
from mortgage_register_processor import MortgageRegisterProcessor
from pymongo import MongoClient
from dotenv import load_dotenv
import certifi

def upload_data():
    load_dotenv()
    
    # Connect to MongoDB
    mongo_uri = os.environ.get("MONGO_URI")
    if not mongo_uri:
        print("MONGO_URI environment variable not set")
        return
        
    print("Connecting to MongoDB...")
    client = MongoClient(mongo_uri, tlsCAFile=certifi.where())
    db = client["sinharealty"]
    
    excel_file = r"C:\Users\Debangshu05\Downloads\SINHAS_Own_Property_Purchase_Mortgage_Register-2 (1).xlsx"
    if not os.path.exists(excel_file):
        print(f"File not found: {excel_file}")
        return
        
    print(f"Processing {excel_file}...")
    processor = MortgageRegisterProcessor(excel_file)
    records = processor.process_register()
    
    if records:
        print(f"Found {len(records)} records. Uploading to MongoDB 'mortgage_register' collection...")
        db['mortgage_register'].delete_many({})
        result = db['mortgage_register'].insert_many(records)
        print(f"Successfully uploaded {len(result.inserted_ids)} records.")
    else:
        print("No valid records found in the Excel file.")

if __name__ == "__main__":
    upload_data()
