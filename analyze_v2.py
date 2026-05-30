import pandas as pd
import json

file_path = "SINHAS_Guest_Client_Database_V2 (1).xlsx"
excel_file = pd.ExcelFile(file_path)

result = {}
for sheet_name in excel_file.sheet_names:
    df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=5)
    result[sheet_name] = df.fillna("").to_dict(orient="records")

print(json.dumps(result, indent=2))
