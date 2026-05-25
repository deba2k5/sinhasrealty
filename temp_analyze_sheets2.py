import pandas as pd
import json

xl = pd.ExcelFile('SINHAS_Guest_Client_Database_V2.xlsx')
out = {}
for s in ['Guest Profiles', 'Property Lookup', 'Revenue Tracker']:
    df = xl.parse(s, header=1)
    out[s] = df.columns.tolist()

with open('columns2.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2)
