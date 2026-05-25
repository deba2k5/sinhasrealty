import pandas as pd

xls = pd.ExcelFile('SINHAS_Guest_Client_Database_V2 (1).xlsx')

# Check header rows for each data sheet
for sheet in ['Guest Profiles', 'Property Lookup', 'Revenue Tracker']:
    print(f'\n=== {sheet} ===')
    for hdr_idx in [0, 1, 2, 3, 4]:
        df = pd.read_excel(xls, sheet, header=hdr_idx, nrows=1)
        cols = list(df.columns)[:8]
        print(f'Header row {hdr_idx}: {cols}')
