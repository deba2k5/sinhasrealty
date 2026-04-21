import pandas as pd

file_path = "Furnishings_Inventory_Final-v1.0.xlsx"
xl = pd.ExcelFile(file_path)

print(f"Sheet names: {xl.sheet_names}")
main_sheet = xl.sheet_names[0]
print(f"Main sheet name: {main_sheet}")

df = xl.parse(main_sheet, header=None, nrows=10)
print(df.iloc[:6, :10])
