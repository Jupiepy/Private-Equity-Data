# Fund Valuation & Reconciliation — Methodology & Automation

> Semi-annual **fund-of-funds (FOF)** valuation reconciliation across 24 sub-funds.
> **All data is synthetic.** Real fund data is omitted per NDA.

A source-linked, rule-based reconciliation pipeline that turns a manual, error-prone
valuation cross-check into an auditable, repeatable process — load heterogeneous
sub-fund reports, validate them against a standard schema, flag discrepancies by
severity, and produce a full audit trail.

## Background

A RMB fund-of-funds platform monitors **24 underlying funds** and performs a
**semi-annual valuation reconciliation**: the master workbook must be consistent
with every sub-fund's reported figures, and every number must be traceable to its
source.

## Problems Solved

1. **Data inconsistency** — sub-funds report in different templates and granularity.
2. **No traceability** — figures without source links cause rework and audit risk.
3. **Manual effort** — cross-checking 20+ files by hand is error-prone and slow.

## Pipeline Overview

| Step | Description |
|---|---|
| 1. Standardize | Auto-detect each sub-fund's template and map columns to a single schema |
| 2. Validate | Run six rule-based checks below |
| 3. Classify | Tag each row by severity: `blocking` / `flagged` / `warning` / `matched` / `missing` |
| 4. Report | Emit reconciliation CSVs + a chart dashboard |

### Validation Rules

| Check | Rule |
|---|---|
| Completeness | Every sub-fund present; no missing `valuation_date` or `fund_id` |
| Arithmetic | `unrealized_pnl = fair_value − cost_basis` (within tolerance) |
| Paid-in vs committed | `paid_in_capital` must not exceed `committed_capital` |
| Sum-to-master | Sub-fund totals must equal the master row within tolerance |
| Cross-quarter | Growth vs prior period must be explainable (no unexplained swings) |
| Source tracing | Every value references `source_file / source_sheet / source_row` |

### Severity Triage

- **Blocking** — breaks totals / missing critical data → return to sub-fund
- **Flagged** — arithmetic mismatch, extreme growth, paid-in over committed → review
- **Warning** — format/semantic, missing date → log with owner + status
- **Matched** — pass

## Repository Structure

```
Private-Equity-Data/
├── README.md              # this file
├── methodology.md         # full step-by-step methodology
├── reconcile.py           # main validation + reconciliation pipeline
├── visualization.py       # chart dashboard (matplotlib / seaborn)
├── requirements.txt       # Python dependencies
└── sample_data/           # synthetic demo data (24 sub-funds + master + history)
    ├── master_template_2026H1.xlsx
    ├── history_2025H2.csv
    └── subfund_01_2026H1.xlsx ... subfund_24_2026H1.xlsx
```

## Quick Start

```bash
# 1. install dependencies
pip install -r requirements.txt

# 2. run the full reconciliation pipeline
python reconcile.py \
  --input sample_data \
  --output reports/ \
  --history sample_data \
  --master sample_data/master_template_2026H1.xlsx
```

> `--history` points to the directory holding the prior-period CSV;
> `--master` points to the master workbook for the sum-to-master check.
> Omit either to skip the corresponding check.

### Outputs (written to `reports/`)

| File | Contents |
|---|---|
| `reconciliation_summary.csv` | per-status counts and totals |
| `flagged_issues.csv` | every flag with rule, reason, and source link |
| `master_consolidated.csv` | validated master workbook |
| `check_detail.csv` | check-by-check pass/fail matrix |

### Visualization

```python
from visualization import plot_reconciliation_dashboard
plot_reconciliation_dashboard(df, save_dir="reports/")
```

Generates a static chart dashboard for the reconciliation results.

## Key Takeaway

A **source-linked, rule-based reconciliation workflow** turns a manual grind into an
auditable, repeatable process — the same discipline applies to any data-heavy finance
task！

## Tech Stack

Python · pandas · NumPy · openpyxl · matplotlib · seaborn

---

*Synthetic demo. No real fund names, figures, or reports are included.*
