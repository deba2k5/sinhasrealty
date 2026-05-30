import openpyxl
import pandas as pd
import json
from datetime import datetime
import re

class MortgageRegisterProcessor:
    """Process Own Property Purchase & Mortgage Register Excel data"""
    
    # Field mapping based on BRD
    FIELD_MAPPING = {
        # Identification
        'Property ID': 'property_id',
        'Property Name / Type / Class': 'property_name',
        
        # Location/Address
        'Address (combined)': 'address',
        'Coordinates (Lat/Long)': 'coordinates',
        
        # Physical Attributes
        'Floor': 'floor',
        'Position': 'position',
        'Rooms': 'rooms',
        'Size (sqm)': 'size_sqm',
        
        # Purchase
        'Purchase Date': 'purchase_date',
        'Purchase Price (CHF)': 'purchase_price',
        'Notary & Land Reg. Costs (CHF)': 'notary_costs',
        'Own Capital / Equity (CHF)': 'own_capital',
        
        # Initial Mortgage
        'Financing Bank (Initial)': 'initial_bank',
        'Financing Type (Initial)': 'initial_financing_type',
        'Interest Rate (Initial) %': 'initial_interest_rate',
        'SARON Margin (Initial) %': 'initial_saron_margin',
        'Initial Mortgage Amount (CHF)': 'initial_mortgage_amount',
        'Mortgage Start Date (Initial)': 'initial_start_date',
        'Mortgage Term (years)': 'initial_term_years',
        'Maturity/Renewal Date (Initial)': 'initial_maturity_date',
        'Amortization Type (Initial)': 'initial_amortization_type',
        'Annual Amortization (Initial) (CHF)': 'initial_annual_amortization',
        'Current Mortgage Outstanding (Initial) (CHF)': 'initial_current_outstanding',
        
        # Refinancing
        'Refinanced? (Yes/No)': 'refinanced_flag',
        'Refinancing Date': 'refinancing_date',
        'Refinancing Reason': 'refinancing_reason',
        'Top-up / Aufstockung (CHF)': 'refinancing_topup',
        'Financing Bank (Refinancing)': 'refinancing_bank',
        'Financing Type (Refinancing)': 'refinancing_financing_type',
        'Interest Rate (Refinancing) %': 'refinancing_interest_rate',
        'SARON Margin (Refinancing) %': 'refinancing_saron_margin',
        'Refinancing Mortgage Amount (CHF)': 'refinancing_mortgage_amount',
        'Refinancing Start Date': 'refinancing_start_date',
        'Refinancing Term (years)': 'refinancing_term_years',
        'Maturity/Renewal Date (Refinancing)': 'refinancing_maturity_date',
        'Amortization Type (Refinancing)': 'refinancing_amortization_type',
        'Annual Amortization (Refinancing) (CHF)': 'refinancing_annual_amortization',
        'Current Mortgage Outstanding (Refinancing) (CHF)': 'refinancing_current_outstanding',
        
        # KPIs
        'Remarks': 'remarks'
    }
    
    def __init__(self, excel_file):
        self.excel_file = excel_file
        self.xls = pd.ExcelFile(excel_file, engine='openpyxl')
        
    def extract_real_headers(self):
        """Extract actual column headers from the Excel sheet"""
        # Read the first 3 rows to understand structure
        df_headers = pd.read_excel(self.excel_file, sheet_name='Own Property Register', header=None, nrows=3)
        print("Header rows:")
        for i, row in df_headers.iterrows():
            print(f"Row {i}: {row.tolist()[:15]}...")
        
    def process_register(self):
        """Process the Own Property Register sheet"""
        # Read with correct header row (row 3 contains actual column names)
        df = pd.read_excel(self.excel_file, sheet_name='Own Property Register', header=3)
        
        print(f"✓ Loaded {len(df)} rows")
        print(f"✓ Columns ({len(df.columns)}): {list(df.columns[:15])}...\n")
        
        # Clean and process records
        records = []
        for idx, row in df.iterrows():
            # Skip rows without Property ID
            if pd.isna(row.iloc[0]) or str(row.iloc[0]).strip() == '':
                continue
                
            record = self.process_row(row)
            if record:
                records.append(record)
        
        return records
    
    def process_row(self, row):
        """Process a single row into a structured record"""
        record = {
            'record_type': 'own_property_mortgage_register',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Extract all fields from the row
        for idx, col in enumerate(row.index):
            field_name = str(col).strip()
            value = row.iloc[idx]
            
            # Skip NaN values
            if pd.isna(value):
                continue
            
            # Clean field name and add to record
            clean_name = self.clean_field_name(field_name)
            record[clean_name] = self.convert_value(field_name, value)
        
        # Calculate KPIs
        record = self.calculate_kpis(record)
        
        return record if record.get('property_id') else None
    
    def clean_field_name(self, field_name):
        """Convert field name to database-safe format"""
        # Remove special chars, convert to snake_case
        name = str(field_name).strip()
        name = re.sub(r'[^\w\s]', '', name)  # Remove special chars
        name = re.sub(r'\s+', '_', name)  # Replace spaces with underscore
        name = name.lower()
        return name
    
    def convert_value(self, field_name, value):
        """Convert value to appropriate type"""
        if pd.isna(value):
            return None
        
        # Handle dates
        if 'date' in field_name.lower():
            try:
                if isinstance(value, str):
                    return pd.to_datetime(value).isoformat()
                else:
                    return pd.to_datetime(value).isoformat()
            except:
                return str(value)
        
        # Handle percentages and numbers
        if any(x in field_name.lower() for x in ['%', 'rate', 'price', 'cost', 'amount', 'outstanding']):
            try:
                return float(value)
            except:
                return str(value)
        
        return str(value)
    
    def calculate_kpis(self, record):
        """Calculate derived KPIs based on BRD requirements"""
        
        # Total Acquisition Cost = Purchase Price + Notary & Land Registry Costs
        try:
            price = record.get('purchase_price', 0) or 0
            notary = record.get('notary_costs', 0) or 0
            record['total_acquisition_cost'] = price + notary
        except:
            pass
        
        # Own Capital % = Own Capital / Purchase Price
        try:
            own_capital = record.get('own_capital', 0) or 0
            price = record.get('purchase_price', 0) or 1
            if price > 0:
                record['own_capital_percent'] = (own_capital / price) * 100
        except:
            pass
        
        # Determine Effective Mortgage (use refinancing if available, else initial)
        effective_mortgage = record.get('refinancing_current_outstanding') or record.get('initial_current_outstanding', 0)
        effective_rate = record.get('refinancing_interest_rate') or record.get('initial_interest_rate', 0)
        
        record['effective_current_mortgage'] = effective_mortgage
        record['effective_interest_rate'] = effective_rate
        
        # LTV % = Effective Mortgage / Purchase Price
        try:
            price = record.get('purchase_price', 0) or 1
            if price > 0 and effective_mortgage:
                record['ltv_percent'] = (effective_mortgage / price) * 100
        except:
            pass
        
        # Annual Interest Cost = Effective Mortgage × Effective Rate
        try:
            if effective_mortgage and effective_rate:
                record['annual_interest_cost'] = effective_mortgage * (effective_rate / 100)
                record['monthly_interest_cost'] = record['annual_interest_cost'] / 12
        except:
            pass
        
        return record
    
    def get_data_dictionary(self):
        """Extract data dictionary and rules from the second sheet"""
        df_dict = pd.read_excel(self.excel_file, sheet_name='Data Dictionary & Rules', header=1)
        return df_dict.to_dict('records')

# Main execution
if __name__ == "__main__":
    excel_file = r"c:\Users\Debangshu05\Downloads\sinharealty\SINHAS_Own_Property_Purchase_Mortgage_Register-2 (1).xlsx"
    
    processor = MortgageRegisterProcessor(excel_file)
    
    print("=" * 80)
    print("PROCESSING MORTGAGE REGISTER")
    print("=" * 80)
    
    processor.extract_real_headers()
    
    try:
        records = processor.process_register()
        
        print(f"\n✓ Processed {len(records)} properties\n")
        
        if records:
            print("Sample record:")
            print(json.dumps(records[0], indent=2, default=str))
            
            print(f"\n✓ Ready for MongoDB upload ({len(records)} properties)")
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
