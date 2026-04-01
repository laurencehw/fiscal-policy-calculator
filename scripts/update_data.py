#!/usr/bin/env python3
"""
Data Update Pipeline Script

Checks and reports on data freshness for:
- IRS SOI tables (vintage year, file format validation)
- FRED API (configuration, cache status)
- CBO baseline (current vintage being used)

Usage:
    python scripts/update_data.py --check              # Report status only
    python scripts/update_data.py --refresh-fred       # Refresh FRED cache
    python scripts/update_data.py --help               # Show options
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fiscal_model.data.irs_soi import IRSSOIData
from fiscal_model.data.fred_data import FREDData
from fiscal_model.baseline import CBOBaseline, BaselineVintage


def check_irs_data():
    """Check IRS SOI data files and report vintage."""
    print("\n" + "=" * 70)
    print("IRS SOI DATA FILES")
    print("=" * 70)

    try:
        irs = IRSSOIData()
        available_years = irs.get_data_years_available()

        if not available_years:
            print("Status: NO FILES FOUND")
            print("Expected location: fiscal_model/data_files/irs_soi/")
            return False

        print(f"Status: Found")
        print(f"Available vintage years: {', '.join(map(str, available_years))}")
        print(f"Most recent year: {max(available_years)}")

        # Validate format of most recent file
        latest_year = max(available_years)
        try:
            # Try to load the data
            data = irs._read_table_1_1(latest_year)
            total_revenue = irs.get_total_revenue(latest_year)
            brackets = irs.get_bracket_distribution(latest_year)

            print(f"\nValidation for {latest_year}:")
            print(f"  - Table rows: {len(data)}")
            print(f"  - Total income tax revenue: ${total_revenue:,.1f}B")
            print(f"  - Income brackets parsed: {len(brackets)}")

            # Show bracket summary
            if brackets:
                min_agi = min(b.agi_floor for b in brackets)
                max_filers = max(b.num_returns for b in brackets)
                print(f"  - AGI range: ${min_agi:,.0f} to $top")
                print(f"  - Largest bracket: {max_filers:,} filers")

            print(f"  - Format: VALID")
            return True
        except Exception as e:
            print(f"  - Format: INVALID - {str(e)}")
            return False

    except Exception as e:
        print(f"Status: ERROR - {str(e)}")
        return False


def check_fred_data():
    """Check FRED API status and cache freshness."""
    print("\n" + "=" * 70)
    print("FRED API AND CACHE")
    print("=" * 70)

    # Check API key
    api_key = os.getenv("FRED_API_KEY", "").strip()
    if api_key:
        print(f"API Key: Configured (length: {len(api_key)} chars)")
    else:
        print("API Key: NOT CONFIGURED (set FRED_API_KEY environment variable)")

    try:
        fred = FREDData()

        print(f"FRED Library: {'Available' if fred.is_available() else 'Not available (fredapi not installed)'}")

        # Check cache status
        cache_files = list(fred.cache_dir.glob("fred_*.json"))
        print(f"\nCache location: {fred.cache_dir}")
        print(f"Cached series: {len(cache_files)}")

        if cache_files:
            print("\nCache status:")
            for series_id in ["GDP", "GDPC1", "UNRATE", "DGS10"]:
                path = fred.cache_dir / f"fred_{series_id}.json"
                if path.exists():
                    mtime = datetime.fromtimestamp(path.stat().st_mtime)
                    age_days = (datetime.utcnow() - mtime).days
                    status = "fresh" if age_days <= fred.cache_max_age_days else "stale"
                    print(f"  - {series_id:12s}: {mtime.strftime('%Y-%m-%d %H:%M')} ({age_days}d, {status})")
                else:
                    print(f"  - {series_id:12s}: NOT CACHED")

        return True

    except Exception as e:
        print(f"Status: ERROR - {str(e)}")
        return False


def check_cbo_baseline():
    """Check current CBO baseline vintage."""
    print("\n" + "=" * 70)
    print("CBO BASELINE")
    print("=" * 70)

    try:
        # Create baseline with default settings
        baseline = CBOBaseline(use_real_data=True)

        print(f"Default vintage: {baseline.baseline_vintage_date}")
        print(f"Start year: {baseline.start_year}")
        print(f"Duration: {baseline.duration} years")

        # Try to get economic assumptions
        assumptions = baseline.assumptions
        print(f"\nEconomic assumptions (Year 1):")
        print(f"  - Real GDP growth: {assumptions.real_gdp_growth[0]:.1%}")
        print(f"  - Inflation: {assumptions.inflation[0]:.1%}")
        print(f"  - Unemployment: {assumptions.unemployment[0]:.2%}")
        print(f"  - 10-year rate: {assumptions.interest_rate_10yr[0]:.2%}")

        # Try to generate projection
        proj = baseline.generate()
        print(f"\nBaseline projection generated:")
        print(f"  - GDP (Y1): ${proj.nominal_gdp[0]:,.1f}B")
        print(f"  - Total revenues (Y1): ${proj.total_revenues[0]:,.1f}B")
        print(f"  - Total outlays (Y1): ${proj.total_outlays[0]:,.1f}B")
        print(f"  - 10-year deficit: ${proj.get_cumulative_deficit():,.1f}B")

        return True

    except Exception as e:
        print(f"Status: ERROR - {str(e)}")
        return False


def refresh_fred_cache():
    """Attempt to refresh FRED cache."""
    print("\n" + "=" * 70)
    print("REFRESHING FRED CACHE")
    print("=" * 70)

    try:
        fred = FREDData()

        if not fred.is_available():
            print("FRED API not available. Cannot refresh.")
            print("Install fredapi: pip install fredapi")
            print("Set FRED_API_KEY environment variable")
            return False

        print("Attempting to fetch fresh data from FRED API...")
        success = fred.refresh()

        if success:
            print("SUCCESS: FRED cache refreshed")
            return True
        else:
            print("FAILED: Could not refresh FRED cache")
            if fred._last_error:
                print(f"Error: {fred._last_error}")
            return False

    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False


def print_summary(irs_ok, fred_ok, cbo_ok):
    """Print overall data freshness summary."""
    print("\n" + "=" * 70)
    print("DATA FRESHNESS SUMMARY")
    print("=" * 70)

    statuses = [
        ("IRS SOI data", irs_ok),
        ("FRED API/cache", fred_ok),
        ("CBO baseline", cbo_ok),
    ]

    for name, status in statuses:
        symbol = "✓" if status else "✗"
        print(f"{symbol} {name}")

    all_ok = all(s for _, s in statuses)
    if all_ok:
        print("\nAll data sources are operational.")
    else:
        print("\nSome data sources need attention. See details above.")

    return all_ok


def main():
    parser = argparse.ArgumentParser(
        description="Check and update fiscal policy calculator data sources."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check data status without making changes (default behavior)"
    )
    parser.add_argument(
        "--refresh-fred",
        action="store_true",
        help="Refresh FRED API cache (requires API key)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print additional diagnostic information"
    )

    args = parser.parse_args()

    # If no action specified, default to --check
    if not (args.check or args.refresh_fred):
        args.check = True

    print("\nFiscal Policy Calculator - Data Update Pipeline")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if args.refresh_fred:
        # Refresh FRED and then check everything
        refresh_ok = refresh_fred_cache()
        irs_ok = check_irs_data()
        fred_ok = check_fred_data()
        cbo_ok = check_cbo_baseline()
    else:
        # Just check
        irs_ok = check_irs_data()
        fred_ok = check_fred_data()
        cbo_ok = check_cbo_baseline()

    all_ok = print_summary(irs_ok, fred_ok, cbo_ok)

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
