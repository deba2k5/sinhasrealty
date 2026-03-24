import pandas as pd
from pymongo import MongoClient
import sys
import os

# ==========================================
# CONFIGURATION
# Update this with your actual MongoDB connection string
# ==========================================
MONGO_URI = 'mongodb+srv://sinhasrealty:sinhasrealty@sinhasrealty.cqt4cec.mongodb.net/?appName=sinhasrealty'

def create_template(filename="sinharealty_template.xlsx"):
    """Generates an empty Excel file with correct columns."""
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        pd.DataFrame(columns=['city_name', 'canton', 'country', 'postal_code_prefix', 'is_active']).to_excel(writer, sheet_name='cities', index=False)
        pd.DataFrame(columns=['city_id', 'property_code', 'property_name', 'street_address', 'postal_code', 'building_type', 'total_floors', 'total_units', 'furnished_standard']).to_excel(writer, sheet_name='properties', index=False)
        pd.DataFrame(columns=['property_id', 'unit_type_id', 'occupancy_type_id', 'unit_code', 'unit_name', 'floor_no', 'apartment_no', 'bedrooms', 'bathrooms', 'area_sqm', 'furnished']).to_excel(writer, sheet_name='units', index=False)
    print(f"✅ Successfully created Excel template: {filename}")

def create_dummy_data(filename="sinharealty_data.xlsx"):
    """Generates an Excel file pre-filled with test dataset."""
    print(f"📝 Generating dummy data Excel file '{filename}'...")
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        pd.DataFrame([
            {'city_name': 'Zürich', 'canton': 'Zürich', 'country': 'Switzerland', 'postal_code_prefix': '80', 'is_active': True},
            {'city_name': 'Basel', 'canton': 'Basel-Stadt', 'country': 'Switzerland', 'postal_code_prefix': '40', 'is_active': True}
        ]).to_excel(writer, sheet_name='cities', index=False)
        
        pd.DataFrame([
            {'city_id': 1, 'property_code': 'ZUR-01', 'property_name': 'Zurich Central Suites', 'street_address': 'Bahnhofstrasse 10', 'postal_code': '8001', 'building_type': 'mixed-use', 'total_floors': 5, 'total_units': 20, 'furnished_standard': True},
            {'city_id': 2, 'property_code': 'BAS-01', 'property_name': 'Basel Riverside', 'street_address': 'Rheingasse 15', 'postal_code': '4058', 'building_type': 'apartment building', 'total_floors': 4, 'total_units': 15, 'furnished_standard': True}
        ]).to_excel(writer, sheet_name='properties', index=False)
        
        pd.DataFrame([
            {'property_id': 1, 'unit_type_id': 1, 'occupancy_type_id': 1, 'unit_code': 'ZUR-ST-05', 'unit_name': 'Zurich Business Studio', 'floor_no': '2', 'apartment_no': '205', 'bedrooms': 0, 'bathrooms': 1, 'area_sqm': 45.00, 'furnished': True},
            {'property_id': 2, 'unit_type_id': 2, 'occupancy_type_id': 1, 'unit_code': 'BAS-1B-01', 'unit_name': 'Basel River View 1BR', 'floor_no': '1', 'apartment_no': '101', 'bedrooms': 1, 'bathrooms': 1, 'area_sqm': 60.00, 'furnished': True}
        ]).to_excel(writer, sheet_name='units', index=False)
    print(f"✅ Dummy data file generated perfectly.")

def import_data(filename, use_test_db=False):
    """Reads Excel and imports data to the database."""
    if not os.path.exists(filename):
        print(f"❌ Error: Cannot find the file '{filename}'")
        return

    db_type = "MONGODB TEST DB" if use_test_db else "MONGODB PROD DB"
    db_name = "test_sinharealty" if use_test_db else "sinharealty"
    print(f"🔌 Connecting to database: {db_type} ({db_name})...")
    
    try:
        client = MongoClient(MONGO_URI)
        client.admin.command('ping')
        db = client[db_name]
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return

    print(f"📂 Reading Excel file '{filename}'...")
    try:
        xls = pd.ExcelFile(filename, engine='openpyxl')
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            df = df.dropna(how='all')
            if not df.empty:
                print(f"⏳ Importing {len(df)} rows into collection '{sheet_name}'...")
                if use_test_db:
                    db[sheet_name].drop() # equivalent to if_exists='replace'
                
                records = df.to_dict('records')
                if records:
                    db[sheet_name].insert_many(records)
                print(f"✅ Successfully inserted into {sheet_name}")
            else:
                print(f"⏭️ Skipping empty sheet: {sheet_name}")
                
        print(f"\n🎉 All data imported successfully to {db_type}!")
    except Exception as e:
        print(f"❌ Failed during import: {e}")

if __name__ == "__main__":
    print("========================================")
    print(" SINHA'S GmbH Excel to MongoDB Tool     ")
    print("========================================\n")
    
    if len(sys.argv) > 1 and sys.argv[1] == '--template':
        create_template("sinharealty_template.xlsx")
    elif len(sys.argv) > 1 and sys.argv[1] == '--test':
        create_dummy_data("sinharealty_data.xlsx")
        import_data("sinharealty_data.xlsx", use_test_db=True)
    elif len(sys.argv) > 1:
        import_data(sys.argv[1])
    else:
        print("Usage Instructions:")
        print("  1. Run Test (Creates dummy data & imports to test_sinharealty DB):")
        print("     python import_from_excel.py --test\n")
        print("  2. Create a blank template:")
        print("     python import_from_excel.py --template\n")
        print("  3. Import your actual filled Excel file (to MongoDB):")
        print("     python import_from_excel.py your_filled_file.xlsx\n")
