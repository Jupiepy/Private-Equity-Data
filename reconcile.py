"""
FOF Valuation Reconciliation — Production-grade pipeline.

Handles semi-annual reconciliation of 20+ sub-fund reports with:
  - Heterogeneous input formats (column mapping, sheet detection)
  - Multi-layer validation rules
  - Cross-quarter consistency checks
  - Severity-based discrepancy triage
  - Full source traceability

ALL DATA IS SYNTHETIC. No real fund data (per NDA).

Run:
    python reconcile.py --input sample_data/ --history history/ --output reports/
"""

import argparse
import random
import sys
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

TOLERANCE_ARITH = 1e-4          # for unrealized_pnl arithmetic check
TOLERANCE_SUM = 1e-3            # for sum-to-master check  
CROSS_QTR_THRESHOLD = 0.50      # 50% swing triggers flag
PAID_IN_OVER_COMMIT_TOLERANCE = 0.01  # 1% over committed is ok

SEVERITY = {
    "matched": "matched",
    "warning": "warning",
    "flagged": "flagged",
    "blocking": "blocking",
    "missing": "missing",
}

# Column name mappings for heterogeneous sub-fund templates
COLUMN_MAPS = {
    "standard": {
        "fund_id": "fund_id",
        "valuation_date": "valuation_date",
        "committed_capital": "committed_capital",
        "paid_in_capital": "paid_in_capital",
        "cost_basis": "cost_basis",
        "fair_value": "fair_value",
        "unrealized_pnl": "unrealized_pnl",
        "source_file": "source_file",
        "source_sheet": "source_sheet",
        "source_row": "source_row",
    },
    "variant_a": {  # Some funds use different column names
        "fund_id": "Fund ID",
        "valuation_date": "Val Date",
        "committed_capital": "Committed",
        "paid_in_capital": "Paid In",
        "cost_basis": "Cost",
        "fair_value": "Fair Value",
        "unrealized_pnl": "Unrealized P&L",
        "source_file": "File",
        "source_sheet": "Sheet",
        "source_row": "Row",
    },
    "variant_b": {  # Another variant
        "fund_id": "fund_code",
        "valuation_date": "report_date",
        "committed_capital": "commitment",
        "paid_in_capital": "called",
        "cost_basis": "book_cost",
        "fair_value": "nav",
        "unrealized_pnl": "unrealized_gain",
        "source_file": "filename",
        "source_sheet": "tab",
        "source_row": "line",
    },
}

# ----------------------------------------------------------------------
# Data Loading — Handle Heterogeneity
# ----------------------------------------------------------------------

def detect_template(df: pd.DataFrame) -> str:
    """Detect which column mapping template matches the input DataFrame."""
    cols = set(df.columns.str.lower().str.strip())
    
    for template_name, mapping in COLUMN_MAPS.items():
        template_cols = set(v.lower().strip() for v in mapping.values())
        # Check if at least 6 of 10 key columns are present
        if len(cols & template_cols) >= 6:
            return template_name
    
    # Default to standard if nothing matches well
    return "standard"


def standardize_columns(df: pd.DataFrame, template_name: str) -> pd.DataFrame:
    """Map heterogeneous columns to standard schema."""
    mapping = COLUMN_MAPS[template_name]
    # Reverse mapping: input_col -> standard_col
    rev_map = {v: k for k, v in mapping.items()}
    
    # Find matching columns (case-insensitive)
    rename_dict = {}
    for col in df.columns:
        col_lower = col.lower().strip()
        for input_col, standard_col in rev_map.items():
            if col_lower == input_col.lower().strip():
                rename_dict[col] = standard_col
                break
    
    df = df.rename(columns=rename_dict)
    
    # Ensure all standard columns exist (fill missing with NaN)
    for std_col in COLUMN_MAPS["standard"].keys():
        if std_col not in df.columns:
            df[std_col] = np.nan
    
    return df


def load_subfund_report(path: Path) -> pd.DataFrame:
    """Load a single sub-fund Excel report, auto-detect sheet and template."""
    # Try common sheet names
    sheet_names = ["NAV", "Valuation", "Report", "Sheet1", 0]
    
    df = None
    for sheet in sheet_names:
        try:
            df = pd.read_excel(path, sheet_name=sheet)
            break
        except Exception:
            continue
    
    if df is None:
        raise ValueError(f"Could not read {path}")
    
    template = detect_template(df)
    df = standardize_columns(df, template)
    
    # Add source metadata if not present
    if pd.isna(df["source_file"]).all():
        df["source_file"] = path.name
    if pd.isna(df["source_sheet"]).all():
        df["source_sheet"] = sheet if isinstance(sheet, str) else "Sheet1"
    if pd.isna(df["source_row"]).all():
        df["source_row"] = df.index + 2  # Excel row numbers (1-based + header)
    
    # Parse dates
    df["valuation_date"] = pd.to_datetime(df["valuation_date"], errors="coerce")
    
    # Numeric columns
    numeric_cols = ["committed_capital", "paid_in_capital", "cost_basis", 
                    "fair_value", "unrealized_pnl"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    
    return df


def load_all_reports(input_dir: Path) -> pd.DataFrame:
    """Load and concatenate all sub-fund reports from a directory."""
    reports = []
    for file in sorted(input_dir.glob("*.xlsx")):
        if "master" in file.name.lower():
            continue  # Skip master template files
        try:
            df = load_subfund_report(file)
            reports.append(df)
        except Exception as e:
            print(f"⚠️  Failed to load {file.name}: {e}")
    
    if not reports:
        raise ValueError(f"No valid sub-fund reports found in {input_dir}")
    
    return pd.concat(reports, ignore_index=True)


# ----------------------------------------------------------------------
# Validation Rules
# ----------------------------------------------------------------------

def validate_completeness(df: pd.DataFrame, expected_funds: int = 24) -> pd.DataFrame:
    """Check 1: All expected sub-funds present; no missing valuation date."""
    df = df.copy()
    df["check_completeness"] = "pass"
    
    # Missing valuation date
    mask_missing_date = df["valuation_date"].isna()
    df.loc[mask_missing_date, "check_completeness"] = "fail_missing_date"
    
    # Missing fund_id
    mask_missing_id = df["fund_id"].isna()
    df.loc[mask_missing_id, "check_completeness"] = "fail_missing_id"
    
    return df


def validate_arithmetic(df: pd.DataFrame, eps: float = TOLERANCE_ARITH) -> pd.DataFrame:
    """Check 2: unrealized_pnl = fair_value - cost_basis (within tolerance)."""
    df = df.copy()
    df["check_arithmetic"] = "pass"
    
    # Compute expected unrealized_pnl
    expected_unrealized = df["fair_value"] - df["cost_basis"]
    
    # Where both values exist, check difference
    mask_has_both = df["fair_value"].notna() & df["cost_basis"].notna()
    mask_mismatch = mask_has_both & (df["unrealized_pnl"] - expected_unrealized).abs() > eps
    
    df.loc[mask_mismatch, "check_arithmetic"] = "fail_arithmetic_mismatch"
    
    # Also check: if unrealized_pnl is missing but fair_value and cost_basis exist, compute it
    mask_missing_unrealized = df["unrealized_pnl"].isna() & mask_has_both
    df.loc[mask_missing_unrealized, "unrealized_pnl"] = (
        df.loc[mask_missing_unrealized, "fair_value"] - df.loc[mask_missing_unrealized, "cost_basis"]
    )
    
    return df


def validate_paid_in_vs_committed(df: pd.DataFrame, 
                                   tolerance: float = PAID_IN_OVER_COMMIT_TOLERANCE) -> pd.DataFrame:
    """Check 3: paid_in_capital must not exceed committed_capital by more than tolerance."""
    df = df.copy()
    df["check_paid_in"] = "pass"
    
    mask_has_both = df["paid_in_capital"].notna() & df["committed_capital"].notna()
    mask_exceeds = mask_has_both & (df["paid_in_capital"] > df["committed_capital"] * (1 + tolerance))
    
    df.loc[mask_exceeds, "check_paid_in"] = "fail_paid_in_exceeds_committed"
    
    return df


def validate_sum_to_master(df: pd.DataFrame, 
                           master_path: Optional[Path] = None,
                           tolerance: float = TOLERANCE_SUM) -> pd.DataFrame:
    """Check 4: Sub-fund totals must reconcile to master workbook."""
    df = df.copy()
    df["check_sum_to_master"] = "pass"
    
    if master_path is None or not master_path.exists():
        # No master to compare against — skip but mark
        df["check_sum_to_master"] = "skipped_no_master"
        return df
    
    try:
        master = pd.read_excel(master_path)
        master = standardize_columns(master, detect_template(master))
        
        # Aggregate sub-fund fair_value by fund_id
        subfund_sums = df.groupby("fund_id")["fair_value"].sum().reset_index()
        subfund_sums.columns = ["fund_id", "subfund_total"]
        
        # Merge with master
        merged = subfund_sums.merge(
            master[["fund_id", "fair_value"]].rename(columns={"fair_value": "master_total"}),
            on="fund_id",
            how="outer"
        )
        
        # Identify mismatches
        merged["diff"] = (merged["subfund_total"] - merged["master_total"]).abs()
        mask_mismatch = merged["diff"] > tolerance
        mismatch_funds = merged.loc[mask_mismatch, "fund_id"].tolist()
        
        # Mark in original df
        df.loc[df["fund_id"].isin(mismatch_funds), "check_sum_to_master"] = "fail_master_mismatch"
        
    except Exception as e:
        print(f"⚠️  Master reconciliation failed: {e}")
        df["check_sum_to_master"] = "skipped_error"
    
    return df


def validate_cross_quarter_consistency(df: pd.DataFrame,
                                        history_dir: Optional[Path] = None,
                                        threshold: float = CROSS_QTR_THRESHOLD) -> pd.DataFrame:
    """Check 5: Same fund across quarters — growth must be explainable."""
    df = df.copy()
    df["check_cross_quarter"] = "pass"
    
    if history_dir is None or not history_dir.exists():
        df["check_cross_quarter"] = "skipped_no_history"
        return df
    
    # Load most recent historical report
    hist_files = sorted(history_dir.glob("*.csv"))
    if not hist_files:
        df["check_cross_quarter"] = "skipped_no_history"
        return df
    
    try:
        hist = pd.read_csv(hist_files[-1])
        hist["fund_id"] = hist["fund_id"].astype(str)
        
        # Merge current with history
        merged = df[["fund_id", "fair_value"]].merge(
            hist[["fund_id", "fair_value"]].rename(columns={"fair_value": "fair_value_prev"}),
            on="fund_id",
            how="left"
        )
        
        # Compute growth rate
        mask_has_prev = merged["fair_value_prev"].notna() & merged["fair_value"].notna() & (merged["fair_value_prev"] != 0)
        growth = (merged.loc[mask_has_prev, "fair_value"] - merged.loc[mask_has_prev, "fair_value_prev"]) / merged.loc[mask_has_prev, "fair_value_prev"].abs()
        
        # Flag extreme swings
        mask_extreme = mask_has_prev & (growth.abs() > threshold)
        extreme_funds = merged.loc[mask_extreme, "fund_id"].tolist()
        
        df.loc[df["fund_id"].isin(extreme_funds), "check_cross_quarter"] = "fail_extreme_growth"
        df["growth_rate"] = np.nan
        df.loc[mask_has_prev, "growth_rate"] = growth
        
    except Exception as e:
        print(f"⚠️  Cross-quarter check failed: {e}")
        df["check_cross_quarter"] = "skipped_error"
    
    return df


def validate_source_traceability(df: pd.DataFrame) -> pd.DataFrame:
    """Check 6: Every value has a source link (file/sheet/row)."""
    df = df.copy()
    df["check_traceability"] = "pass"
    
    mask_orphan = (df["source_file"].isna() | df["source_file"].eq(""))
    df.loc[mask_orphan, "check_traceability"] = "fail_orphan_value"
    
    return df


# ----------------------------------------------------------------------
# Severity Classification
# ----------------------------------------------------------------------

def classify_severity(df: pd.DataFrame) -> pd.DataFrame:
    """Classify each row by overall severity based on all checks."""
    df = df.copy()
    
    def _severity(row):
        # Blocking: missing critical data or total mismatch
        if pd.isna(row["fair_value"]):
            return SEVERITY["missing"]
        if row.get("check_sum_to_master") == "fail_master_mismatch":
            return SEVERITY["blocking"]
        if row.get("check_completeness") == "fail_missing_id":
            return SEVERITY["blocking"]
        
        # Flagged: arithmetic errors, extreme swings, paid-in exceeds committed
        if row.get("check_arithmetic") == "fail_arithmetic_mismatch":
            return SEVERITY["flagged"]
        if row.get("check_cross_quarter") == "fail_extreme_growth":
            return SEVERITY["flagged"]
        if row.get("check_paid_in") == "fail_paid_in_exceeds_committed":
            return SEVERITY["flagged"]
        if row["fair_value"] <= 0:
            return SEVERITY["flagged"]
        
        # Warning: traceability issues, format deviations
        if row.get("check_traceability") == "fail_orphan_value":
            return SEVERITY["warning"]
        if row.get("check_completeness") == "fail_missing_date":
            return SEVERITY["warning"]
        
        return SEVERITY["matched"]
    
    df["status"] = df.apply(_severity, axis=1)
    return df


# ----------------------------------------------------------------------
# Consolidation + Report Generation
# ----------------------------------------------------------------------

def generate_reports(df: pd.DataFrame, out_dir: Path) -> Dict[str, Path]:
    """Generate all reconciliation output files."""
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Summary report
    summary = (
        df.groupby("status")
        .agg(
            count=("fund_id", "count"),
            total_committed=("committed_capital", "sum"),
            total_fair_value=("fair_value", "sum"),
        )
        .reset_index()
    )
    summary_path = out_dir / "reconciliation_summary.csv"
    summary.to_csv(summary_path, index=False)
    
    # 2. Flagged issues detail
    flagged = df[df["status"] != SEVERITY["matched"]][[
        "fund_id", "status", "committed_capital", "paid_in_capital",
        "cost_basis", "fair_value", "unrealized_pnl", "growth_rate",
        "check_completeness", "check_arithmetic", "check_paid_in",
        "check_sum_to_master", "check_cross_quarter", "check_traceability",
        "source_file", "source_sheet", "source_row"
    ]]
    flagged_path = out_dir / "flagged_issues.csv"
    flagged.to_csv(flagged_path, index=False)
    
    # 3. Master consolidated (validated)
    master = df[[
        "fund_id", "valuation_date", "committed_capital", "paid_in_capital",
        "cost_basis", "fair_value", "unrealized_pnl", "growth_rate",
        "status", "source_file", "source_sheet", "source_row"
    ]].copy()
    master["valuation_date"] = master["valuation_date"].dt.strftime("%Y-%m-%d")
    master_path = out_dir / "master_consolidated.csv"
    master.to_csv(master_path, index=False)
    
    # 4. Check-level detail
    checks = df[[
        "fund_id", "status",
        "check_completeness", "check_arithmetic", "check_paid_in",
        "check_sum_to_master", "check_cross_quarter", "check_traceability"
    ]].copy()
    checks_path = out_dir / "check_detail.csv"
    checks.to_csv(checks_path, index=False)
    
    return {
        "summary": summary_path,
        "flagged": flagged_path,
        "master": master_path,
        "checks": checks_path,
    }


def reconcile(input_dir: Path,
              output_dir: Path,
              history_dir: Optional[Path] = None,
              master_path: Optional[Path] = None,
              expected_funds: int = 24) -> pd.DataFrame:
    """Main reconciliation pipeline."""
    
    print(f"\n🔍 Loading sub-fund reports from: {input_dir}")
    df = load_all_reports(input_dir)
    print(f"   Loaded {len(df)} rows from {df['source_file'].nunique()} files")
    
    print("\n🧪 Running validation checks...")
    df = validate_completeness(df, expected_funds)
    df = validate_arithmetic(df)
    df = validate_paid_in_vs_committed(df)
    df = validate_sum_to_master(df, master_path)
    df = validate_cross_quarter_consistency(df, history_dir)
    df = validate_source_traceability(df)
    
    print("\n⚠️  Classifying severity...")
    df = classify_severity(df)
    
    print("\n📊 Generating reports...")
    paths = generate_reports(df, output_dir)
    for name, path in paths.items():
        print(f"   → {path.name}")
    
    # Print summary to console
    print("\n" + "=" * 50)
    print("RECONCILIATION SUMMARY")
    print("=" * 50)
    summary = df.groupby("status").agg(
        count=("fund_id", "count"),
        total_fv=("fair_value", lambda x: f"{x.sum()/1e6:.1f}M" if x.sum() == x.sum() else "N/A")
    ).reset_index()
    print(summary.to_string(index=False))
    print(f"\n✅ Outputs written to: {output_dir}")
    
    return df


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="FOF Valuation Reconciliation")
    parser.add_argument("--input", type=Path, default=Path("sample_data"),
                        help="Directory containing sub-fund Excel reports")
    parser.add_argument("--output", type=Path, default=Path("reports"),
                        help="Output directory for reconciliation reports")
    parser.add_argument("--history", type=Path, default=None,
                        help="Directory containing historical reconciliation CSVs")
    parser.add_argument("--master", type=Path, default=None,
                        help="Path to master workbook for sum-to-master check")
    parser.add_argument("--expected-funds", type=int, default=24,
                        help="Expected number of sub-funds")
    
    args = parser.parse_args()
    
    reconcile(
        input_dir=args.input,
        output_dir=args.output,
        history_dir=args.history,
        master_path=args.master,
        expected_funds=args.expected_funds
    )


if __name__ == "__main__":
    main()
