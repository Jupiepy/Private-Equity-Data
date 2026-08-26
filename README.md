# Fund Valuation & Reconciliation — Methodology & Automation

> Semi-annual **fund-of-funds (FOF)** valuation reconciliation across 20+ sub-funds.
> **All data shown is synthetic. Real fund data is omitted per NDA.**

## Background

A RMB fund-of-funds platform monitors **20+ underlying funds** and performs a **semi-annual valuation reconciliation**: the master workbook must be consistent with every sub-fund's reported figures, with each number traceable to its source.

## Problems Solved

1. **Data inconsistency** — sub-funds report in different templates and granularity.
2. **No traceability** — figures without source links cause rework and audit risk.
3. **Manual effort** — cross-checking 20+ files by hand is error-prone and slow.

## Approach

### Step 1 — Standardized template
Define one required column set for every sub-fund submission:

```
fund_id | valuation_date | asset_class | fair_value | unrealized_pnl | source_file | source_sheet | source_row | remark
```

### Step 2 — Cross-check logic
| Check | Rule |
|---|---|
| Completeness | Every sub-fund present; no missing valuation date |
| Sum-to-master | Sub-fund totals must equal the master row within tolerance |
| Consistency | Same fund across quarters: growth must be explainable (no unexplained jumps) |
| Source tracing | Every value references `source_file / sheet / row` |

### Step 3 — Flag & resolve
Discrepancies are flagged by severity:
- **Blocking** (breaks totals) → back to the sub-fund for correction
- **Warning** (format/semantic) → recorded in a review log with owner & status

### Step 4 — Automation (Python, synthetic demo)
`scripts/` contains a small pipeline that:
- reads a folder of (synthetic) sub-fund Excel reports,
- validates against the template,
- produces a reconciliation report: matched / flagged / missing.

## Key Takeaway
A **source-linked, rule-based reconciliation workflow** turns a manual grind into an auditable, repeatable process — the same discipline applies to any data-heavy finance task.

## Files
- `methodology.md` — full step-by-step methodology
- `scripts/` — Python demo on synthetic data
- `scripts/sample_data/` — generated synthetic sub-fund reports (no real data)
