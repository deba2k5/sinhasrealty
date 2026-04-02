from pymongo import MongoClient
import certifi
import os

url = 'mongodb+srv://sinhasrealty:sinhasrealty@sinhasrealty.cqt4cec.mongodb.net/?appName=sinhasrealty'
client = MongoClient(url, tlsCAFile=certifi.where())
db = client['sinharealty']
col = db['sinhasrealty data']
doc = col.find_one()

if doc:
    print("Keys in 'sinhasrealty data':")
    for key in doc.keys():
        print(f"'{key}'")
else:
    print("Collection is empty.")
