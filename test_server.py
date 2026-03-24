import requests

url = "http://127.0.0.1:5000/upload_occupancy"
files = {'file': open('ORIGINAL TOTAL APARTMENTS AND AVAILIBILITY -with details -6.3.26.xlsx', 'rb')}
print("Sending request...")
try:
    response = requests.post(url, files=files)
    print("Status:", response.status_code)
    print("Response:", response.json())
except Exception as e:
    print("Error:", e)
