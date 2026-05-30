import pandas as pd

df = pd.read_excel(
    r'c:\Users\Debangshu05\Downloads\sinharealty\SINHAS_Own_Property_Purchase_Mortgage_Register-2 (1).xlsx',
    sheet_name='Own Property Register',
    header=3
)

print("First property data:")
for i in range(min(20, len(df.columns))):
    print(f"{i:2d}. {df.columns[i]:35s}: {df.iloc[0, i]}")
