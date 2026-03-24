import pandas as pd
import json

filename = "ORIGINAL TOTAL APARTMENTS AND AVAILIBILITY -with details -6.3.26.xlsx"
try:
    # Read skipping the first row as the actual headers are on the second row
    df = pd.read_excel(filename, sheet_name='OCCUPANCY -Apartment', header=1)
    
    # Rename unnamed columns if necessary, but head() will show
    print("Columns:", df.columns.tolist())
    print("\nFirst 3 rows:")
    for record in df.head(3).to_dict('records'):
        print(record)
        
    print("\nCity Breakdown:")
    print(df['City'].value_counts(dropna=False))
except Exception as e:
    print(f"Error: {e}")
