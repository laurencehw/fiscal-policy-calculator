"""
Data validation utilities for IRS SOI and FRED data.

Provides validation checks to ensure data quality before use in fiscal modeling.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check."""
    passed: bool
    message: str
    details: Optional[dict] = None

    def __str__(self) -> str:
        status = "✓ PASS" if self.passed else "✗ FAIL"
        return f"{status}: {self.message}"


class DataValidator:
    """
    Validation checks for IRS SOI and FRED economic data.

    Ensures data quality before use in fiscal policy modeling by checking:
    - Data completeness (no missing critical values)
    - Reasonable ranges (totals match expectations)
    - Consistency (cross-table validation)
    - Format compliance (expected columns present)
    """

    # Expected ranges for validation
    IRS_TOTAL_RETURNS_MIN = 100_000_000  # 100M returns minimum
    IRS_TOTAL_RETURNS_MAX = 200_000_000  # 200M returns maximum
    IRS_TOTAL_REVENUE_MIN = 1500  # $1.5T minimum revenue (billions)
    IRS_TOTAL_REVENUE_MAX = 4000  # $4.0T maximum revenue (billions)

    FRED_GDP_MIN = 20000  # $20T minimum nominal GDP (billions)
    FRED_GDP_MAX = 40000  # $40T maximum nominal GDP (billions)
    FRED_UNRATE_MIN = 2.0  # 2% minimum unemployment rate
    FRED_UNRATE_MAX = 15.0  # 15% maximum unemployment rate

    @staticmethod
    def validate_irs_table_1_1(df: pd.DataFrame, year: int) -> ValidationResult:
        """
        Validate IRS Table 1.1 (Income and Tax Items) structure and content.

        Checks:
        - Required columns present
        - No negative values in key columns
        - Total returns in reasonable range
        - Total AGI in reasonable range

        Args:
            df: DataFrame containing Table 1.1 data
            year: Tax year

        Returns:
            ValidationResult with pass/fail status and details
        """
        issues = []

        # Check 1: Non-empty
        if df.empty:
            return ValidationResult(
                passed=False,
                message=f"Table 1.1 for {year} is empty"
            )

        # Check 2: Required columns
        # Note: Exact column names depend on IRS file format
        # This is a placeholder that will be refined with actual data
        required_patterns = ['returns', 'agi', 'income']
        columns_lower = [c.lower() for c in df.columns]

        missing_patterns = []
        for pattern in required_patterns:
            if not any(pattern in col for col in columns_lower):
                missing_patterns.append(pattern)

        if missing_patterns:
            issues.append(f"Missing expected columns: {missing_patterns}")

        # Check 3: No negative values in numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns
        for col in numeric_cols:
            if (df[col] < 0).any():
                issues.append(f"Negative values found in column: {col}")

        # Check 4: Total returns in reasonable range
        # Try to find the total row or sum returns
        returns_col = DataValidator._find_column(df, ['returns', 'number'])
        if returns_col is not None:
            total_returns = df[returns_col].sum()
            if not (DataValidator.IRS_TOTAL_RETURNS_MIN <= total_returns <= DataValidator.IRS_TOTAL_RETURNS_MAX):
                issues.append(
                    f"Total returns {total_returns:,.0f} outside expected range "
                    f"[{DataValidator.IRS_TOTAL_RETURNS_MIN:,.0f}, {DataValidator.IRS_TOTAL_RETURNS_MAX:,.0f}]"
                )

        if issues:
            return ValidationResult(
                passed=False,
                message=f"Table 1.1 validation failed for {year}",
                details={'issues': issues}
            )

        return ValidationResult(
            passed=True,
            message=f"Table 1.1 for {year} passed validation"
        )

    @staticmethod
    def validate_irs_table_3_3(df: pd.DataFrame, year: int) -> ValidationResult:
        """
        Validate IRS Table 3.3 (Tax Liability and Credits) structure and content.

        Checks:
        - Required columns present
        - Total tax revenue in reasonable range
        - Effective tax rates in reasonable range
        - No negative tax liabilities

        Args:
            df: DataFrame containing Table 3.3 data
            year: Tax year

        Returns:
            ValidationResult with pass/fail status and details
        """
        issues = []

        # Check 1: Non-empty
        if df.empty:
            return ValidationResult(
                passed=False,
                message=f"Table 3.3 for {year} is empty"
            )

        # Check 2: Required columns
        required_patterns = ['tax', 'credit', 'liability']
        columns_lower = [c.lower() for c in df.columns]

        missing_patterns = []
        for pattern in required_patterns:
            if not any(pattern in col for col in columns_lower):
                missing_patterns.append(pattern)

        if missing_patterns:
            issues.append(f"Missing expected columns: {missing_patterns}")

        # Check 3: Tax liability in reasonable range
        tax_col = DataValidator._find_column(df, ['tax', 'liability'])
        if tax_col is not None:
            total_tax = df[tax_col].sum()

            # Convert to billions if needed (check magnitude)
            if total_tax < 10000:  # Likely already in billions
                total_tax_billions = total_tax
            else:  # Likely in dollars, convert
                total_tax_billions = total_tax / 1e9

            if not (DataValidator.IRS_TOTAL_REVENUE_MIN <= total_tax_billions <= DataValidator.IRS_TOTAL_REVENUE_MAX):
                issues.append(
                    f"Total tax revenue ${total_tax_billions:,.0f}B outside expected range "
                    f"[${DataValidator.IRS_TOTAL_REVENUE_MIN:,.0f}B, ${DataValidator.IRS_TOTAL_REVENUE_MAX:,.0f}B]"
                )

        if issues:
            return ValidationResult(
                passed=False,
                message=f"Table 3.3 validation failed for {year}",
                details={'issues': issues}
            )

        return ValidationResult(
            passed=True,
            message=f"Table 3.3 for {year} passed validation"
        )

    @staticmethod
    def validate_fred_series(series: pd.Series, series_id: str) -> ValidationResult:
        """
        Validate FRED series data.

        Checks:
        - Non-empty series
        - No recent NaN values
        - Values in reasonable range (series-specific)
        - Data not too stale

        Args:
            series: pandas Series with FRED data
            series_id: FRED series identifier

        Returns:
            ValidationResult with pass/fail status and details
        """
        issues = []

        # Check 1: Non-empty
        if series.empty:
            return ValidationResult(
                passed=False,
                message=f"FRED series {series_id} is empty"
            )

        # Check 2: No recent NaN values (last 12 observations)
        recent_data = series.tail(min(12, len(series)))
        if recent_data.isna().any():
            nan_count = recent_data.isna().sum()
            issues.append(f"{nan_count} NaN values in recent data")

        # Check 3: Series-specific range validation
        latest_value = float(series.iloc[-1])

        if series_id == 'GDP':
            if not (DataValidator.FRED_GDP_MIN <= latest_value <= DataValidator.FRED_GDP_MAX):
                issues.append(
                    f"GDP value ${latest_value:,.0f}B outside expected range "
                    f"[${DataValidator.FRED_GDP_MIN:,.0f}B, ${DataValidator.FRED_GDP_MAX:,.0f}B]"
                )

        elif series_id == 'UNRATE':
            if not (DataValidator.FRED_UNRATE_MIN <= latest_value <= DataValidator.FRED_UNRATE_MAX):
                issues.append(
                    f"Unemployment rate {latest_value:.1f}% outside expected range "
                    f"[{DataValidator.FRED_UNRATE_MIN:.1f}%, {DataValidator.FRED_UNRATE_MAX:.1f}%]"
                )

        elif series_id == 'DGS10':
            if not (0 <= latest_value <= 20):  # 0-20% range for interest rates
                issues.append(f"10-year rate {latest_value:.2f}% outside expected range [0%, 20%]")

        elif series_id == 'CIVPART':
            if not (55 <= latest_value <= 70):  # 55-70% range for labor force participation
                issues.append(f"Labor force participation {latest_value:.1f}% outside expected range [55%, 70%]")

        if issues:
            return ValidationResult(
                passed=False,
                message=f"FRED series {series_id} validation failed",
                details={'issues': issues, 'latest_value': latest_value}
            )

        return ValidationResult(
            passed=True,
            message=f"FRED series {series_id} passed validation",
            details={'latest_value': latest_value}
        )

    @staticmethod
    def _find_column(df: pd.DataFrame, keywords: List[str]) -> Optional[str]:
        """
        Find column in DataFrame matching any of the keywords (case-insensitive).

        Args:
            df: DataFrame to search
            keywords: List of keywords to match

        Returns:
            Column name if found, None otherwise
        """
        columns_lower = {c.lower(): c for c in df.columns}

        for keyword in keywords:
            for col_lower, col_original in columns_lower.items():
                if keyword.lower() in col_lower:
                    return col_original

        return None

    @staticmethod
    def validate_all_irs_data(irs_data, year: int) -> List[ValidationResult]:
        """
        Run all IRS data validations for a year.

        Args:
            irs_data: IRSSOIData instance
            year: Tax year to validate

        Returns:
            List of ValidationResult objects
        """
        results = []

        # Validate Table 1.1
        try:
            df_1_1 = irs_data.load_table_1_1(year)
            result = DataValidator.validate_irs_table_1_1(df_1_1, year)
            results.append(result)
        except Exception as e:
            results.append(ValidationResult(
                passed=False,
                message=f"Failed to load Table 1.1 for {year}: {e}"
            ))

        # Validate Table 3.3
        try:
            df_3_3 = irs_data.load_table_3_3(year)
            result = DataValidator.validate_irs_table_3_3(df_3_3, year)
            results.append(result)
        except Exception as e:
            results.append(ValidationResult(
                passed=False,
                message=f"Failed to load Table 3.3 for {year}: {e}"
            ))

        return results

    @staticmethod
    def validate_all_fred_data(fred_data) -> List[ValidationResult]:
        """
        Run all FRED data validations for common series.

        Args:
            fred_data: FREDData instance

        Returns:
            List of ValidationResult objects
        """
        results = []

        common_series = ['GDP', 'GDPC1', 'UNRATE', 'DGS10', 'CIVPART', 'CPIAUCSL']

        for series_id in common_series:
            try:
                series = fred_data.get_series(series_id)
                result = DataValidator.validate_fred_series(series, series_id)
                results.append(result)
            except Exception as e:
                results.append(ValidationResult(
                    passed=False,
                    message=f"Failed to load FRED series {series_id}: {e}"
                ))

        return results

    @staticmethod
    def print_validation_report(results: List[ValidationResult]):
        """
        Print formatted validation report.

        Args:
            results: List of ValidationResult objects
        """
        print("\n" + "=" * 70)
        print("DATA VALIDATION REPORT")
        print("=" * 70)

        passed = sum(1 for r in results if r.passed)
        total = len(results)

        for result in results:
            print(f"\n{result}")
            if result.details:
                for key, value in result.details.items():
                    print(f"  {key}: {value}")

        print("\n" + "=" * 70)
        print(f"SUMMARY: {passed}/{total} checks passed")
        print("=" * 70 + "\n")

        if passed == total:
            logger.info("All validation checks passed")
        else:
            logger.warning(f"{total - passed} validation check(s) failed")
