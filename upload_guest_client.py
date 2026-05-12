import requests
import sys

def upload_file(filepath):
    url = 'http://127.0.0.1:5000/upload_guest_client'
    try:
        with open(filepath, 'rb') as f:
            files = {'file': (filepath, f)}
            response = requests.post(url, files=files)
            print("Status Code:", response.status_code)
            print("Response:", response.json())
    except Exception as e:
        print("Error uploading file:", e)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        upload_file(sys.argv[1])
    else:
        upload_file('SINHAS_Guest_Client_Database_V2.xlsx')
