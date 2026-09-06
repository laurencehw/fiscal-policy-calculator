# IRS Statistics of Income Data

This directory contains IRS Statistics of Income (SOI) Individual Income Tax Statistics data files used for accurate tax revenue estimation.

## Data Source

**URL:** https://www.irs.gov/statistics/soi-tax-stats-individual-income-tax-statistics

**Publisher:** Internal Revenue Service, Statistics of Income Division

**Update Frequency:** Annual (typically released ~2 years after tax year)

## Required Data Files

### Tax Year 2021

1. **Table 1.1 - All Returns: Selected Income and Tax Items**
   - Download from: Individual Income Tax Returns 2021, Table 1.1
   - Save as: `table_1_1_2021.csv`
   - Contains: Number of returns, AGI, taxable income by AGI bracket

2. **Table 3.3 - All Returns: Tax Liability, Tax Credits, and Tax Payments**
   - Download from: Individual Income Tax Returns 2021, Table 3.3
   - Save as: `table_3_3_2021.csv`
   - Contains: Tax liability, effective tax rates by AGI bracket

### Tax Year 2022

1. **Table 1.1 - All Returns: Selected Income and Tax Items**
   - Download from: Individual Income Tax Returns 2022, Table 1.1
   - Save as: `table_1_1_2022.csv`
   - Contains: Number of returns, AGI, taxable income by AGI bracket

2. **Table 3.3 - All Returns: Tax Liability, Tax Credits, and Tax Payments**
   - Download from: Individual Income Tax Returns 2022, Table 3.3
   - Save as: `table_3_3_2022.csv`
   - Contains: Tax liability, effective tax rates by AGI bracket

### Tax Year 2023 — Table 1.2 (by filing status)

**Table 1.2 - All Returns: Adjusted Gross Income, Deductions, and Tax Items, by
Size of Adjusted Gross Income and by Filing Status**

- Source workbook: <https://www.irs.gov/pub/irs-soi/23in12ms.xls>
- Publication: IRS, Statistics of Income Division, *Individual Income Tax
  Returns Complete Report* (Publication 1304), March 2026
- Saved as: `table_1_2_2023.csv`
- Rebuilt by: `python scripts/build_filing_status_data.py`
- Contains: the same 19 AGI size classes as Table 1.1, split five ways — all
  returns; married filing jointly and surviving spouses; married filing
  separately; heads of households; single — with returns, AGI, itemised and
  standard deductions, taxable income, income tax after credits and total
  income tax for each.

**Why it is here and how it is used.** Statutory income-tax thresholds are
stated per filing status (CBO's Option 46 surtax at "$20,000 for single filers
and $40,000 for joint filers"; the 2025 24% bracket at $206,700 joint against
$103,350 otherwise). `IRSSOIData.get_bracket_distribution_by_status` reads this
table for the **composition** of each AGI class only — Table 1.1 still supplies
the level — because Table 1.2's taxable-income column is measured on *all*
returns where Table 1.1's is measured on *taxable* returns, a 2.7% difference
that has nothing to do with filing status. Apportioning keeps the split exactly
neutral: a per-status base evaluated at one uniform threshold reproduces the
pooled `get_filers_by_bracket` result to the cent.

The `.xls` workbooks are **not** tracked (`.gitignore` excludes `*.xls`); the
CSVs are the auditable artefacts and the build script re-downloads the source.

## Download Instructions

### Step 1: Navigate to IRS SOI Website
1. Go to https://www.irs.gov/statistics/soi-tax-stats-individual-income-tax-statistics
2. Scroll down to find the year you want (e.g., "SOI Tax Stats - Individual Income Tax Returns Publication 1304 (Complete Report)")

### Step 2: Download Excel Files
1. Click on the link for Tax Year 2021 or 2022
2. Look for "Table 1.1 - All Returns: Selected Income and Tax Items" - click to download Excel file
3. Look for "Table 3.3 - All Returns: Tax Liability, Tax Credits, and Tax Payments" - click to download Excel file
4. Repeat for other tax years as needed

### Step 3: Convert to CSV Format
The IRS provides Excel files (.xlsx) but our code expects CSV format. You have two options:

**Option A: Excel Manual Conversion**
1. Open the Excel file
2. Go to File > Save As
3. Choose "CSV (Comma delimited) (*.csv)" as the file type
4. Save with the filename format: `table_X_X_YYYY.csv` (e.g., `table_1_1_2021.csv`)

**Option B: Python Script (if you have pandas installed)**
```python
import pandas as pd

# For Table 1.1
df = pd.read_excel('downloaded_table_1_1_2021.xlsx', skiprows=3)  # Skip header rows
df.to_csv('table_1_1_2021.csv', index=False)

# For Table 3.3
df = pd.read_excel('downloaded_table_3_3_2021.xlsx', skiprows=3)
df.to_csv('table_3_3_2021.csv', index=False)
```

### Step 4: Verify File Format
The CSV files should have columns similar to:
- **Table 1.1:** Size of adjusted gross income, Number of returns, Amount of AGI, Amount of taxable income, etc.
- **Table 3.3:** Size of adjusted gross income, Number of returns, Income tax after credits, Effective tax rate, etc.

## Data Years Needed

**Minimum:** 1 year (most recent available, typically 2022 as of 2024)
**Recommended:** 2-3 years (2021-2022 or 2020-2022) for:
- Validation and cross-checking
- Trend analysis
- Handling data lags

## File Naming Convention

Use this exact naming format:
- `table_1_1_2021.csv`
- `table_1_1_2022.csv`
- `table_3_3_2021.csv`
- `table_3_3_2022.csv`

The data loader expects this specific naming pattern.

## Data Quality Checks

After downloading, verify:
1. **Completeness:** All AGI brackets present (typically ~15-20 brackets from $1 to $10M+)
2. **Totals:** Total returns should be ~150-160 million for recent years
3. **Revenue:** Total income tax should be ~$2-2.5 trillion for recent years
4. **No missing values:** Critical columns (returns, AGI, tax) should have no blanks

## Alternative Sources

If IRS website is unavailable, you can also find SOI data at:
- **Tax Policy Center:** https://www.taxpolicycenter.org/statistics
- **NBER Tax Simulator:** https://users.nber.org/~taxsim/ (requires registration)

## Data Usage

Once files are in place, the `IRSSOIData` class will automatically:
- Load and parse CSV files
- Validate data quality
- Provide methods to query by income bracket
- Calculate total revenue for baseline projections
- Auto-populate tax policy parameters

## Questions or Issues?

If you encounter:
- **Format changes:** IRS occasionally changes table formats. Check column names match expected.
- **Missing years:** Use most recent available; code will handle data lags.
- **Large file sizes:** Tables are typically <5MB, no performance issues expected.

---

**Last Updated:** 2024-11-26
**Next Update:** Check IRS website in October 2025 for 2023 data release
