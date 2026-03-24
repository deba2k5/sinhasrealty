from pymongo import MongoClient
import certifi
import time

url = 'mongodb+srv://sinhasrealty:sinhasrealty@sinhasrealty.cqt4cec.mongodb.net/?appName=sinhasrealty'

print("Connecting...")
t0 = time.time()
try:
    client = MongoClient(url, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
    print("Ping:", client.admin.command('ping'))
    print("Find:", client['test'].test.find_one())
    print("Connected safely in", time.time() - t0)
except Exception as e:
    print("Failed in", time.time() - t0)
    print(type(e), e)
