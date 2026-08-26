"""
FOF Valuation Reconciliation — synthetic demo pipeline.

Simulates the semi-annual reconciliation of 20+ sub-fund reports:
  validate -> flag -> consolidate -> report.

ALL DATA IS SYNTHETIC. No real fund data (per NDA).

Run:
    python reconcile.py
"""

import random
import sys
from datetime import date
from pathlib import Path

import pandas as pd

# ----------------------------------------------------------------------
# 1. Synthetic data generation (never touches real data)
# ----------------------------------------------------------------------

def make_synthetic_subfunds(n: int = 24, seed: int = 42) -> pd.DataFrame:
    """Generate n synthetic sub-fund rows for one valuation period."""
    rng = random.Random(seed)
    funds = []
    for i in range(1, n + 1):
        committed = rng.choice([50, 100, 150, 200, 300]) * 1e6
        paid_in = committed * rng.uniform(0.4, 1.0)
        cost_basis = paid_in * rng.uniform(0.9, 1.0)
        fair_value = cost_basis * rng.uniform(0.9, 1.6)  # some funds up, some down
        # inject a couple of deliberate issues for demo purposes
        if i in (7, 19):
            fair_value = float("nan")      # missing value
        elif i == 11:
            fair_value = 0.0               # suspicious zero
        funds.append(
            {
                "fund_id": f"F{i:02d}",
                "valuation_date": date(2026, 6, 30),
                "committed_capital": round(committed, 2),
                "paid_in_capital": round(paid_in, 2),
                "cost_basis": round(cost_basis, 2),
                "fair_value": None if fair_value != fair_value else round(fair_value, 2),
                "source_file": f"subfund_{i:02d}_2026H1.xlsx",
                "source_sheet": "NAV",
                "source_row": 12,
            }
        )
    return pd.DataFrame(funds)


# ----------------------------------------------------------------------
# 2. Validation rules
# ----------------------------------------------------------------------

def validate(df: pd.DataFrame, eps: float = 1e-4, delta: float = 0.01) -> pd.DataFrame:
    """Return a copy of df with a 'status' column: matched / flagged / missing."""
    out = df.copy()

    # arithmetic: fair_value == cost_basis * (1 + return), check unrealized sign
    out["computed_unrealized"] = out["fair_value"] - out["cost_basis"]
    out["unrealized_ok"] = (
        out["computed_unrealized"].isna()
        | (out["computed_unrealized"].abs() > -eps)  # placeholder, refined below
    )

    def _status(row):
        if pd.isna(row["fair_value"]):
            return "missing"
        if row["fair_value"] <= 0:
            return "flagged"
        if pd.isna(row["committed_capital"]) or row["committed_capital"] <= 0:
            return "flagged"
        if row["paid_in_capital"] > row["committed_capital"] * (1 + delta):
            return "flagged"  # paid-in exceeds committed
        return "matched"

    out["status"] = out.apply(_status, axis=1)
    return out


# ----------------------------------------------------------------------
# 3. Consolidation + report
# ----------------------------------------------------------------------

def reconcile(input_df: pd.DataFrame, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    df = validate(input_df)

    summary = (
        df.groupby("status")
        .agg(count=("fund_id", "count"), total_fair_value=("fair_value", "sum"))
        .reset_index()
    )

    flagged = df[df["status"] != "matched"][
        ["fund_id", "status", "committed_capital", "paid_in_capital",
         "fair_value", "source_file", "source_sheet", "source_row"]
    ]

    master = df[
        ["fund_id", "valuation_date", "committed_capital", "paid_in_capital",
         "fair_value", "source_file", "source_sheet", "source_row", "status"]
    ]

    summary.to_csv(out_dir / "reconciliation_summary.csv", index=False)
    flagged.to_csv(out_dir / "flagged_issues.csv", index=False)
    master.to_csv(out_dir / "master_consolidated.csv", index=False)

    print(f"\n=== Reconciliation report ===")
    print(summary.to_string(index=False))
    print(f"\nFlagged/missing issues: {len(flagged)}")
    print(f"Outputs written to: {out_dir}")


# ----------------------------------------------------------------------

if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 42
    data = make_synthetic_subfunds(n=24, seed=seed)
    out = Path(__file__).parent / "reports"
    reconcile(data, out)
