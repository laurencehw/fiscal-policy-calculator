#!/usr/bin/env python3
"""
Batch Policy Scoring Script

Reads a CSV of policy parameters and outputs scoring results.
Useful for parameter sweeps and sensitivity analysis.

Input CSV columns (required):
    - name: Policy description
    - rate_change: Tax rate change (e.g., 0.01 for +1pp)
    - threshold: Income threshold in dollars (e.g., 400000)
    - eti: Elasticity of taxable income (e.g., 0.25)

Output CSV columns:
    - name: Policy name
    - rate_change: Input rate change
    - threshold: Input threshold
    - eti: Input elasticity
    - static_10y: 10-year static revenue effect (billions)
    - behavioral_10y: Behavioral offset (billions)
    - final_10y: Final 10-year revenue effect (billions)
    - marginal_rate: Effective marginal tax rate (percent)
    - affected_filers: Number of affected filers (millions)

Usage:
    python scripts/batch_score.py --help                          # Show help
    python scripts/batch_score.py input.csv output.csv            # Score policies
    python scripts/batch_score.py input.csv output.csv --dynamic  # With dynamic scoring
    python scripts/batch_score.py --example                       # Create example input

Examples:
    Create example input:
        python scripts/batch_score.py --example

    Score with static analysis:
        python scripts/batch_score.py policies.csv results.csv

    Score with dynamic effects (GDP feedback):
        python scripts/batch_score.py policies.csv results.csv --dynamic
"""

import argparse
import sys
import csv
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fiscal_model import FiscalPolicyScorer, TaxPolicy
from fiscal_model.data import IRSSOIData
from fiscal_model.policies import PolicyType


def load_policy_csv(csv_path):
    """Load policies from CSV file."""
    policies = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV file is empty or has no header row")

        required_cols = {'name', 'rate_change', 'threshold', 'eti'}
        missing = required_cols - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        for i, row in enumerate(reader, start=2):  # Start at line 2 (after header)
            try:
                policy = {
                    'name': row['name'].strip(),
                    'rate_change': float(row['rate_change']),
                    'threshold': float(row['threshold']),
                    'eti': float(row['eti']),
                }
                policies.append(policy)
            except (ValueError, KeyError) as e:
                print(f"Warning: Skipping row {i}: {e}", file=sys.stderr)
                continue

    return policies


def score_policy(scorer, policy_dict, dynamic=False):
    """Score a single policy and return results."""
    try:
        import numpy as np

        # Create TaxPolicy object
        policy = TaxPolicy(
            name=policy_dict['name'],
            description=f"Tax rate adjustment: {policy_dict['rate_change']*100:+.1f}pp above ${policy_dict['threshold']:,.0f}",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=policy_dict['rate_change'],
            affected_income_threshold=policy_dict['threshold'],
            taxable_income_elasticity=policy_dict['eti'],
        )

        # Score it
        result = scorer.score_policy(policy, dynamic=dynamic)

        # Get affected filer count from IRS data
        irs = IRSSOIData()
        filer_data = irs.get_filers_by_bracket(year=2022, threshold=policy_dict['threshold'])
        affected_filers = filer_data['num_filers_millions']

        # Calculate effective marginal rate at threshold
        # Simplified: assume 37% top rate (current law)
        marginal_rate = 0.37 + policy_dict['rate_change']

        # Sum the 10-year arrays to get totals
        static_10y = float(np.sum(result.static_revenue_effect))
        behavioral_10y = float(np.sum(result.behavioral_offset))
        final_10y = float(np.sum(result.final_deficit_effect))

        return {
            'name': policy_dict['name'],
            'rate_change': policy_dict['rate_change'],
            'threshold': policy_dict['threshold'],
            'eti': policy_dict['eti'],
            'static_10y': static_10y,
            'behavioral_10y': behavioral_10y,
            'final_10y': final_10y,
            'marginal_rate': marginal_rate,
            'affected_filers': affected_filers,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        # Return error row
        return {
            'name': policy_dict['name'],
            'rate_change': policy_dict['rate_change'],
            'threshold': policy_dict['threshold'],
            'eti': policy_dict['eti'],
            'static_10y': None,
            'behavioral_10y': None,
            'final_10y': None,
            'marginal_rate': None,
            'affected_filers': None,
            'error': str(e),
        }


def save_results_csv(results, output_path):
    """Save results to CSV file."""
    if not results:
        raise ValueError("No results to save")

    fieldnames = [
        'name', 'rate_change', 'threshold', 'eti',
        'static_10y', 'behavioral_10y', 'final_10y',
        'marginal_rate', 'affected_filers'
    ]

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            # Filter to only fieldnames
            row = {k: result.get(k) for k in fieldnames}
            writer.writerow(row)


def create_example_csv(output_path):
    """Create an example input CSV."""
    examples = [
        {
            'name': 'Biden $400K+ (2.6pp)',
            'rate_change': 0.026,
            'threshold': 400000,
            'eti': 0.25,
        },
        {
            'name': 'TCJA Extension (rates)',
            'rate_change': -0.02,
            'threshold': 1000000,
            'eti': 0.25,
        },
        {
            'name': 'Millionaire Tax (2pp)',
            'rate_change': 0.02,
            'threshold': 1000000,
            'eti': 0.25,
        },
        {
            'name': 'Small Business Relief (-0.5pp)',
            'rate_change': -0.005,
            'threshold': 200000,
            'eti': 0.25,
        },
    ]

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'rate_change', 'threshold', 'eti'])
        writer.writeheader()
        writer.writerows(examples)

    print(f"Created example input: {output_path}")
    print("\nExample contents:")
    for ex in examples:
        print(f"  - {ex['name']}: {ex['rate_change']*100:+.1f}pp above ${ex['threshold']:,.0f}")


def print_summary(results):
    """Print summary of scoring results."""
    print("\n" + "=" * 80)
    print("BATCH SCORING RESULTS SUMMARY")
    print("=" * 80)

    successful = [r for r in results if 'error' not in r]
    failed = [r for r in results if 'error' in r]

    print(f"\nScored: {len(successful)} policies")
    if failed:
        print(f"Failed: {len(failed)} policies")

    if successful:
        print("\nResult summary:")
        print(f"{'Policy':<30} {'Static (10y)':<15} {'Behavioral':<15} {'Final (10y)':<15}")
        print("-" * 75)
        for r in successful:
            static = r['static_10y']
            behavioral = r['behavioral_10y']
            final = r['final_10y']

            static_str = f"${static:,.0f}B" if static is not None else "N/A"
            behavioral_str = f"${behavioral:,.0f}B" if behavioral is not None else "N/A"
            final_str = f"${final:,.0f}B" if final is not None else "N/A"

            name_short = r['name'][:28]
            print(f"{name_short:<30} {static_str:>14} {behavioral_str:>14} {final_str:>14}")

    if failed:
        print("\nFailed policies:")
        for r in failed:
            print(f"  - {r['name']}: {r['error']}")


def main():
    parser = argparse.ArgumentParser(
        description="Score fiscal policies in batch from CSV file."
    )
    parser.add_argument(
        'input',
        nargs='?',
        help='Input CSV file with policy parameters'
    )
    parser.add_argument(
        'output',
        nargs='?',
        help='Output CSV file for results'
    )
    parser.add_argument(
        '--example',
        action='store_true',
        help='Create example input CSV (example_policies.csv) and exit'
    )
    parser.add_argument(
        '--dynamic',
        action='store_true',
        help='Include dynamic scoring (GDP feedback effects)'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Print detailed output during scoring'
    )

    args = parser.parse_args()

    # Handle --example mode
    if args.example:
        output = args.input or 'example_policies.csv'
        create_example_csv(output)
        return 0

    # Require input and output if not in example mode
    if not args.input or not args.output:
        parser.print_help()
        print("\n" + "=" * 70)
        print("Examples:")
        print("  Create example input:")
        print("    python scripts/batch_score.py --example")
        print("\n  Score policies:")
        print("    python scripts/batch_score.py policies.csv results.csv")
        print("\n  Score with dynamic effects:")
        print("    python scripts/batch_score.py policies.csv results.csv --dynamic")
        return 1

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        return 1

    print(f"Batch Policy Scoring")
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print(f"Mode:   {'Dynamic' if args.dynamic else 'Static'}")

    try:
        # Load policies
        print(f"\nLoading policies from {input_path}...")
        policies = load_policy_csv(input_path)
        print(f"Loaded {len(policies)} policies")

        # Initialize scorer
        print(f"\nInitializing scorer...")
        scorer = FiscalPolicyScorer(use_real_data=True)

        # Score each policy
        print(f"\nScoring policies...")
        results = []
        for i, policy_dict in enumerate(policies, start=1):
            if args.verbose:
                print(f"  [{i}/{len(policies)}] {policy_dict['name']}")
            result = score_policy(scorer, policy_dict, dynamic=args.dynamic)
            results.append(result)

        # Save results
        print(f"\nSaving results to {output_path}...")
        save_results_csv(results, output_path)

        # Print summary
        print_summary(results)

        print(f"\nSuccess: Results saved to {output_path}")
        return 0

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
