import pandas as pd
import json

file_path = "SINHAS_Guest_Client_Database_V2 (1).xlsx"
excel_file = pd.ExcelFile(file_path)

result = {}
for sheet_name in ["Guest Profiles", "Revenue Tracker"]:
    if sheet_name in excel_file.sheet_names:
        # Read the top row (which has the groups)
        df_group = pd.read_excel(file_path, sheet_name=sheet_name, header=None, nrows=4)
        
        # Row 0 usually has the group names, row 2 or 3 has the actual column names.
        # Let's just dump the first 4 rows to see what is where.
        result[sheet_name] = df_group.fillna("").to_dict(orient="records")

print(json.dumps(result, indent=2))
