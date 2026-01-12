import sys
import os
import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from fiscal_model.microsim.data_builder import build_tax_microdata # Ensure we can find the file path logic if needed
from fiscal_model.microsim.data_generator import SyntheticPopulation
from fiscal_model.microsim.engine import MicroTaxCalculator
from pathlib import Path

def demo_microsim():
    print("--- MICROSIMULATION PROTOTYPE ---\n")
    
    # 1. Load Real Data if available
    real_data_path = Path(__file__).parent / "tax_microdata_2024.csv"
    if real_data_path.exists():
        print(f"1. Loading REAL CPS ASEC Data from {real_data_path.name}...")
        population = pd.read_csv(real_data_path)
    else:
        print("1. Generating synthetic population (100,000 households)...")
        pop_gen = SyntheticPopulation(size=100_000)
        population = pop_gen.generate()
    
    # Calculate total weighted AGI
    # Note: Synthetic generator used 'weight' column, real data also has 'weight'
    total_agi = (population['agi'] * population['weight']).sum()
    print(f"   Total Agi: ${total_agi / 1e9:,.1f}B")
    
    # Weighted avg wage
    avg_wage = (population['wages'] * population['weight']).sum() / population['weight'].sum()
    print(f"   Avg Wage:  ${avg_wage:,.0f}")
    
    # 2. Baseline Score
    print("\n2. Scoring Baseline (Current Law)...")
    calc = MicroTaxCalculator()
    baseline = calc.calculate(population)
    
    total_rev_baseline = (baseline['final_tax'] * baseline['weight']).sum() / 1e9
    print(f"   Total Revenue: ${total_rev_baseline:.1f}B")
    
    # 3. Reform: Double Child Tax Credit
    print("\n3. Scoring Reform: Double CTC to $4,000...")
    
    def double_ctc_reform(c):
        c.ctc_amount = 4000
        
    reform_res = calc.run_reform(population, double_ctc_reform)
    total_rev_reform = (reform_res['final_tax'] * reform_res['weight']).sum() / 1e9
    
    print(f"   Total Revenue: ${total_rev_reform:.1f}B")
    print(f"   Revenue Change: ${total_rev_reform - total_rev_baseline:.1f}B")
    
    # 4. Distributional Analysis (The "JCT" Power)
    print("\n4. Distributional Analysis (Reform Impact)...")
    
    # Merge results
    comparison = baseline.copy()
    comparison.loc[:, 'reform_tax'] = reform_res['final_tax'].values
    comparison.loc[:, 'tax_change'] = comparison['reform_tax'] - comparison['final_tax']

    # Analyze by number of children (something aggregate models struggle with)
    print("\n   Avg Tax Cut by Number of Children:")
    grouped = comparison.groupby('children', group_keys=False).apply(
        lambda x: np.average(x['tax_change'], weights=x['weight']), include_groups=False
    )
    print(grouped)

    # Analyze by Income Decile
    comparison.loc[:, 'decile'] = pd.qcut(comparison['agi'], 10, labels=False, duplicates='drop')
    print("\n   Avg Tax Cut by Income Decile (Top 3):")
    grouped_inc = comparison.groupby('decile', group_keys=False).apply(
        lambda x: np.average(x['tax_change'], weights=x['weight']), include_groups=False
    )
    print(grouped_inc.tail(3))

if __name__ == "__main__":
    demo_microsim()
