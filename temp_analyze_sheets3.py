import pandas as pd
import json

xl = pd.ExcelFile('SINHAS_Guest_Client_Database_V2.xlsx')
out = {}
for s in ['Guest Profiles', 'Property Lookup', 'Revenue Tracker']:
    df = xl.parse(s, header=None, nrows=10)
    # Convert NaN to None for JSON serialization
    df = df.where(pd.notnull(df), None)
    out[s] = df.values.tolist()

with open('columns_preview.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2)
