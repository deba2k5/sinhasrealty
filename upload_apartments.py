import pandas as pd
from pymongo import MongoClient
import os
from dotenv import load_dotenv
import certifi

# Load connection string
load_dotenv()
mongo_uri = os.getenv("MONGO_URI", "mongodb+srv://rajeev:sinhas2k25@sinhas.uic5p.mongodb.net/?retryWrites=true&w=majority&appName=Sinhas")
client = MongoClient(mongo_uri, tlsCAFile=certifi.where())
db = client['sinharealty']
collection = db['property details data']

def run_ingestion(file_path='Property_Details_V4-RS-04.04.2026-v2.xlsx'):
    print(f"Reading file: {file_path}")
    xls = pd.ExcelFile(file_path)
    
    # Target Sheet: PROPERTY MASTER
    sheet_name = 'PROPERTY MASTER'
    df = pd.read_excel(xls, sheet_name=sheet_name)
    
    # Cleaning: Remove dots and unusual whitespace/tabs for MongoDB keys
    df.columns = [str(c).replace('.', '').replace('\t', ' ').strip() for c in df.columns]
    records = df.to_dict('records')
    
    if records:
        print(f"Found {len(records)} records in Excel.")
        print("Clearing existing records in 'property details data'...")
        collection.delete_many({})
        
        # Insert new records
        print(f"Inserting {len(records)} records...")
        collection.insert_many(records)
        print("Upload complete!")
    else:
        print("No records found to upload.")

if __name__ == '__main__':
    run_ingestion()
