
import pandas as pd
import numpy as np
import os
from pathlib import Path

def build_tax_microdata(data_dir: str, output_file: str = "tax_microdata_2024.csv"):
    """
    Ingest CPS ASEC 2024 CSV files and create a clean microdata file 
    for the fiscal policy calculator. 
    
    Args:
        data_dir: Path to directory containing pppub24.csv and hhpub24.csv
        output_file: Name of the output CSV file (saved in data_dir/..)
    """
    print(f"--- CPS ASEC DATA BUILDER ---")
    print(f"Source: {data_dir}")
    
    # 1. Load Data
    # Only load columns we need to save memory/time
    
    # Person Columns
    p_cols = [
        'PH_SEQ', 'P_SEQ', 'A_LINENO', # IDs
        'A_AGE', 'A_MARITL', 'A_SEX', # Demographics
        'WSAL_VAL', # Wages
        'INT_VAL', # Interest
        'DIV_VAL', # Dividends
        'RNT_VAL', # Rent
        'SS_VAL',  # Social Security
        'UC_VAL',  # Unemployment
        'CAP_VAL', # Capital Gains (Check if exists, sometimes named differently or requires imputation)
        'MARSUPWT', # Weight
        'TAX_INC', # Census taxable income estimate (useful for validation)
        'A_CLSWKR', # Class of worker (for payroll tax)
        'PEDISEYE', 'PEDISREM', # Disability (for checking standard deduction)
    ]
    
    # Household Columns
    h_cols = [
        'H_SEQ', 
        'GESTFIPS', # State
        'HSUP_WGT', # Household Weight
        'H_NUMPER', # Number of persons
    ]
    
    # Robust loading: check which columns actually exist
    # (Census variable names can change slightly year-to-year)
    
    try:
        print("1. Loading Person Record (pppub24.csv)...")
        p_path = os.path.join(data_dir, "pppub24.csv")
        # Read header only first to validate columns
        p_header = pd.read_csv(p_path, nrows=0).columns.tolist()
        use_p_cols = [c for c in p_cols if c in p_header]
        
        # Check for critical missing columns
        if 'WSAL_VAL' not in use_p_cols:
            print("WARNING: WSAL_VAL (Wages) not found. Checking aliases...")
            # Fallback logic could go here
            
        df_p = pd.read_csv(p_path, usecols=use_p_cols)
        print(f"   Loaded {len(df_p):,} person records.")
        
        print("2. Loading Household Record (hhpub24.csv)...")
        h_path = os.path.join(data_dir, "hhpub24.csv")
        h_header = pd.read_csv(h_path, nrows=0).columns.tolist()
        use_h_cols = [c for c in h_cols if c in h_header]
        
        df_h = pd.read_csv(h_path, usecols=use_h_cols)
        print(f"   Loaded {len(df_h):,} household records.")
        
    except FileNotFoundError as e:
        print(f"ERROR: Could not find files. {e}")
        return

    # 2. Merge Data
    print("3. Merging Households and Persons...")
    # CPS matches PH_SEQ (Person) to H_SEQ (Household)
    df = df_p.merge(df_h, left_on='PH_SEQ', right_on='H_SEQ', how='left')
    
    # 3. Create Tax Units
    # This is the tricky part. CPS gives "Households". Tax law applies to "Tax Units".
    # A household can contain multiple tax units (e.g., unmarried roommates).
    # SIMPLIFIED LOGIC FOR PROTOTYPE:
    # - Group by Household (PH_SEQ)
    # - If Married (A_MARITL 1 or 2), group with spouse.
    # - Kids (Age < 19 or Student < 24) attach to head.
    # - Others file separately.
    
    # For this simplified builder, we will aggregate to the HOUSEHOLD level first,
    # treating the Primary Person + Spouse as the unit.
    # Nuanced tax unit construction usually requires a dedicated package (like Tax-Calculator's logic).
    # Here we simulate it by aggregating income by PH_SEQ.
    
    print("4. Aggregating to Tax Units (Simplified Household View)...")
    
    # Define aggregations
    aggs = {
        'WSAL_VAL': 'sum',
        'INT_VAL': 'sum',
        'DIV_VAL': 'sum',
        'RNT_VAL': 'sum',
        'SS_VAL': 'sum',
        'UC_VAL': 'sum',
        'MARSUPWT': 'mean', # Use mean weight of members (roughly) or head
        'A_AGE': 'max', # Max age (for elderly deduction)
        'H_NUMPER': 'first',
    }
    
    # Check optional cols
    if 'CAP_VAL' in df.columns:
        aggs['CAP_VAL'] = 'sum'
    if 'TAX_INC' in df.columns:
        aggs['TAX_INC'] = 'sum'
        
    # Group by Household
    units = df.groupby('PH_SEQ').agg(aggs).reset_index()
    
    # Count children (Age < 17 for CTC)
    kids_count = df[df['A_AGE'] < 17].groupby('PH_SEQ').size().reset_index(name='children_under_17')
    units = units.merge(kids_count, on='PH_SEQ', how='left')
    units['children_under_17'] = units['children_under_17'].fillna(0)
    
    # Determine Marital Status of Head (roughly)
    # Get marital status of reference person (A_LINENO = 1 usually, or just check if 'Married' present)
    # A_MARITL: 1=Married spouse present, 2=Married spouse absent, 3=Widowed, 4=Divorced, 5=Separated, 6=Never married
    
    # Check if ANYONE in household is married (Simplification: assumes one married couple per HH)
    is_married = df[df['A_MARITL'].isin([1])].groupby('PH_SEQ').size().reset_index(name='married_count')
    units = units.merge(is_married, on='PH_SEQ', how='left')
    units['married'] = np.where(units['married_count'] > 0, 1, 0)
    
    # 4. Standardize Variable Names for Fiscal Model
    print("5. Standardizing Variables...")
    
    clean_df = pd.DataFrame()
    clean_df['id'] = units['PH_SEQ']
    clean_df['weight'] = units['MARSUPWT'] / 100 # CPS weights are often scaled? No, MARSUPWT is usually 1.0 = 1 person.
    # Actually, verify weight scaling. ASEC weights sum to US population. 
    
    clean_df['wages'] = units['WSAL_VAL']
    clean_df['interest_income'] = units['INT_VAL']
    clean_df['dividend_income'] = units['DIV_VAL']
    clean_df['capital_gains'] = units.get('CAP_VAL', 0) # Fallback to 0 if missing
    clean_df['social_security'] = units['SS_VAL']
    clean_df['unemployment'] = units['UC_VAL']
    
    clean_df['children'] = units['children_under_17']
    clean_df['married'] = units['married']
    clean_df['age_head'] = units['A_AGE']
    
    # AGI Approximation
    clean_df['agi'] = (clean_df['wages'] + 
                       clean_df['interest_income'] + 
                       clean_df['dividend_income'] + 
                       clean_df['capital_gains'] + 
                       clean_df['unemployment']) 
                       # Note: SS is only partially taxable, handled in calculator
    
    # 5. Save
    output_path = os.path.join(Path(data_dir).parent.parent, "fiscal_model", "microsim", output_file)
    print(f"6. Saving to {output_path}...")
    clean_df.to_csv(output_path, index=False)
    
    print("\n--- SUMMARY ---")
    print(f"Records Created: {len(clean_df):,}")
    print(f"Total Weighted Population: {clean_df['weight'].sum():,.0f}")
    print(f"Total Weighted Wages: ${ (clean_df['wages'] * clean_df['weight']).sum() / 1e9:,.1f}B")
    print("Done.")

if __name__ == "__main__":
    # Default path relative to this script
    # Assumes structure: project/fiscal_model/microsim/data_builder.py
    # Data at: project/data/asecpub24csv
    project_root = Path(__file__).resolve().parents[2]
    base_dir = project_root / "data" / "asecpub24csv"
    
    if base_dir.exists():
        build_tax_microdata(str(base_dir))
    else:
        print(f"Data directory not found at {base_dir}")
        print("Please provide path or ensure data is in project/data/asecpub24csv")
