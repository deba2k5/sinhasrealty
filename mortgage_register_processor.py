import openpyxl
import pandas as pd
import json
from datetime import datetime
import re

class MortgageRegisterProcessor:
    """Process Own Property Purchase & Mortgage Register Excel data"""
    
    # Exact column order from Excel
    EXCEL_COLUMN_ORDER = [
        'Property ID', 'Property Name', 'Type', 'Class', 'Address', 
        'Coordinates (Lat/Long)', 'Floor', 'Position', 'Rooms', 'Size (sqm)',
        'Purchase Date', 'Purchase Price (CHF)', 'Notary & Land Reg. Costs (CHF)', 
        'Total Acquisition Cost (CHF)', 'Own Capital / Equity (CHF)', 'Own Capital %',
        'Financing Bank', 'Financing Type (SARON/Fixed)', 'Interest Rate % p.a.', 
        'SARON Margin %', 'Initial Mortgage Amount (CHF)', 'Mortgage Start Date',
        'Term (Years)', 'Maturity / Renewal Date', 'Amortization Type (Direct/Indirect)',
        'Annual Amortization (CHF)', 'Current Mortgage Outstanding (CHF)',
        'Refinanced? (Yes/No)', 'Refinancing / Top-up Date', 
        'Reason (Renewal/Rate/Top-up/Bank)', 'Top-up Amount – Aufstockung (CHF)',
        'Financing Bank (Refi)', 'Financing Type (SARON/Fixed) (Refi)',
        'Interest Rate % p.a. (Refi)', 'SARON Margin % (Refi)',
        'New Mortgage Amount (CHF)', 'Refinancing Start Date',
        'Term (Years) (Refi)', 'Maturity / Renewal Date (Refi)',
        'Amortization Type (Refi)', 'Annual Amortization (CHF) (Refi)',
        'Current Mortgage Outstanding (Refi) (CHF)',
        'Effective Current Mortgage (CHF)', 'Effective Interest Rate %',
        'Loan-to-Value (LTV) %', 'Annual Interest Cost (CHF)',
        'Monthly Interest Cost (CHF)', 'Remarks'
    ]
    
    def __init__(self, excel_file):
        self.excel_file = excel_file
        self.xls = pd.ExcelFile(excel_file, engine='openpyxl')
        
    def extract_real_headers(self):
        """Extract actual column headers from the Excel sheet"""
        df_headers = pd.read_excel(self.excel_file, sheet_name='Own Property Register', header=None, nrows=3)
        print("Header rows:")
        for i, row in df_headers.iterrows():
            print(f"Row {i}: {row.tolist()[:20]}...")
        
    def process_register(self):
        """Process the Own Property Register sheet"""
        df = pd.read_excel(self.excel_file, sheet_name='Own Property Register', header=3)
        
        print(f"✓ Loaded {len(df)} rows")
        print(f"✓ Columns ({len(df.columns)}): {list(df.columns)}...\n")
        
        records = []
        for idx, row in df.iterrows():
            if pd.isna(row.iloc[0]) or str(row.iloc[0]).strip() == '':
                continue
                
            record = self.process_row(row)
            if record:
                records.append(record)
        
        return records
    
    def process_row(self, row):
        record = {
            'record_type': 'own_property_mortgage_register',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Add all columns in exact Excel order
        for col in self.EXCEL_COLUMN_ORDER:
            if col in row.index:
                value = row[col]
                record[col] = self.convert_value(col, value)
            else:
                record[col] = None
        
        # Calculate KPIs
        record = self.calculate_kpis(record)
        
        return record if record.get('Property ID') else None
    
    def convert_value(self, field_name, value):
        if pd.isna(value):
            return None
        
        if 'date' in field_name.lower():
            try:
                if isinstance(value, str):
                    return pd.to_datetime(value, dayfirst=True).strftime('%d.%m.%Y')
                else:
                    return pd.to_datetime(value, dayfirst=True).strftime('%d.%m.%Y')
            except:
                return str(value)
        
        if any(x in field_name.lower() for x in ['%', 'rate', 'price', 'cost', 'amount', 'outstanding']):
            try:
                return float(value)
            except:
                return str(value)
        
        return str(value)
    
    def calculate_kpis(self, record):
        """Calculate derived KPIs based on Excel formulas"""
        
        # Formula 1: Total Acquisition Cost = Purchase Price + Notary & Land Reg. Costs
        try:
            price = float(record.get('Purchase Price (CHF)') or 0)
            notary = float(record.get('Notary & Land Reg. Costs (CHF)') or 0)
            record['Total Acquisition Cost (CHF)'] = price + notary
        except:
            record['Total Acquisition Cost (CHF)'] = None
        
        # Formula 2: Own Capital % = (Own Capital / Total Acquisition Cost) * 100
        try:
            own_capital = float(record.get('Own Capital / Equity (CHF)') or 0)
            total_acquisition = float(record.get('Total Acquisition Cost (CHF)') or 0)
            if total_acquisition > 0:
                record['Own Capital %'] = (own_capital / total_acquisition) * 100
            else:
                record['Own Capital %'] = None
        except:
            record['Own Capital %'] = None
        
        # Formula 3: Effective Current Mortgage - use Refi if available, else Initial
        effective_mortgage = record.get('Current Mortgage Outstanding (Refi) (CHF)') or record.get('Current Mortgage Outstanding (CHF)')
        if effective_mortgage is None or effective_mortgage == '':
            effective_mortgage = None
        else:
            try:
                effective_mortgage = float(effective_mortgage)
            except:
                effective_mortgage = None
        record['Effective Current Mortgage (CHF)'] = effective_mortgage
        
        # Formula 4: Effective Interest Rate - use Refi if available, else Initial
        effective_rate = record.get('Interest Rate % p.a. (Refi)') or record.get('Interest Rate % p.a.')
        if effective_rate is None or effective_rate == '':
            effective_rate = None
        else:
            try:
                effective_rate = float(effective_rate)
            except:
                effective_rate = None
        record['Effective Interest Rate %'] = effective_rate
        
        # Formula 5: Loan-to-Value (LTV) % = (Effective Current Mortgage / Total Acquisition Cost) * 100
        try:
            total_acquisition = float(record.get('Total Acquisition Cost (CHF)') or 0)
            if total_acquisition > 0 and effective_mortgage:
                record['Loan-to-Value (LTV) %'] = (effective_mortgage / total_acquisition) * 100
            else:
                record['Loan-to-Value (LTV) %'] = None
        except:
            record['Loan-to-Value (LTV) %'] = None
        
        # Formula 6: Annual Interest Cost = Effective Current Mortgage * (Effective Interest Rate / 100)
        try:
            if effective_mortgage and effective_rate:
                record['Annual Interest Cost (CHF)'] = effective_mortgage * (effective_rate / 100)
            else:
                record['Annual Interest Cost (CHF)'] = None
        except:
            record['Annual Interest Cost (CHF)'] = None
        
        # Formula 7: Monthly Interest Cost = Annual Interest Cost / 12
        try:
            annual_interest = float(record.get('Annual Interest Cost (CHF)') or 0)
            if annual_interest > 0:
                record['Monthly Interest Cost (CHF)'] = annual_interest / 12
            else:
                record['Monthly Interest Cost (CHF)'] = None
        except:
            record['Monthly Interest Cost (CHF)'] = None
        
        return record
    
    def get_data_dictionary(self):
        df_dict = pd.read_excel(self.excel_file, sheet_name='Data Dictionary & Rules', header=1)
        return df_dict.to_dict('records')

if __name__ == "__main__":
    excel_file = r"C:\Users\Debangshu05\Downloads\SINHAS_Own_Property_Purchase_Mortgage_Register-2 (1).xlsx"
    processor = MortgageRegisterProcessor(excel_file)
    
    print("="*80)
    print("PROCESSING MORTGAGE REGISTER")
    print("="*80)
    
    processor.extract_real_headers()
    
    try:
        records = processor.process_register()
        print(f"\n✓ Processed {len(records)} properties\n")
        if records:
            print("Sample record:")
            print(json.dumps(records[0], indent=2, default=str))
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
