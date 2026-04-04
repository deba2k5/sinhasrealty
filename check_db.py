import os
from pymongo import MongoClient
import certifi
from dotenv import load_dotenv

# Use absolute path if necessary or just a local relative for the current directory
# Since I'm in c:\Users\Debangshu05\Downloads\sinharealty, I'll use that.

load_dotenv()

mongo_uri = os.getenv("MONGO_URI", "mongodb+srv://rajeev:sinhas2k25@sinhas.uic5p.mongodb.net/?retryWrites=true&w=majority&appName=Sinhas")
client = MongoClient(mongo_uri, tlsCAFile=certifi.where())
db = client['sinharealty']
col = db['property details data']

print(f"Total documents: {col.count_documents({})}")
doc = col.find_one()
if doc:
    print("Sample document keys:")
    for k in doc.keys():
        print(f"'{k}'")
else:
    print("Collection is empty!")
