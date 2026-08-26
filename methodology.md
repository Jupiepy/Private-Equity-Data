# Methodology — FOF Semi-Annual Valuation Reconciliation

> Objective: consolidate **20+ sub-fund** valuation data into one master workbook,
> with **100% traceability** and a **rule-based discrepancy workflow**.
> (Synthetic demo only — no real data per NDA.)

---

## 1. Data Model

### 1.1 Master workbook (output)
One row per sub-fund per valuation period:

| column | description |
|---|---|
| `fund_id` | unique internal ID |
| `fund_name_anonymized` | anonymized label (A01, A02, ...) |
| `valuation_date` | period end date |
| `committed_capital` | as agreed at signing |
| `paid_in_capital` | cumulative called |
| `fair_value` | NAV per sub-fund report |
| `unrealized_pnl` | fair value − cost basis |
| `source` | file/sheet/row of origin |
| `status` | `matched` / `flagged` / `missing` |

### 1.2 Sub-fund submission (input)
Each sub-fund returns a report with the required columns (or a mapping is provided).

---

## 2. Validation Rules

### 2.1 Completeness
- All expected sub-funds received a report.
- `valuation_date` present and equal to period end for all rows.

### 2.2 Arithmetic consistency
- `unrealized_pnl = fair_value − cost_basis` (within tolerance ε).
- Sub-fund sum == master row (within tolerance δ).
- Sequential-period growth must be within an explainable band; outside band → flag for commentary.

### 2.3 Traceability
- Every master figure links to `source_file / source_sheet / source_row`.
- No "orphan" values.

---

## 3. Discrepancy Workflow

```
 detect → classify → notify → resolve → re-verify → close
```

| severity | example | action |
|---|---|---|
| **Blocking** | total mismatch, missing period | return to sub-fund; cannot close until fixed |
| **Warning** | format deviation, missing remark | log in review register with owner + due date |
| **Info** | cosmetic | record only |

---

## 4. Automation Pipeline (Python)

```
sub-fund reports (xlsx) ──> validator ──> reconciliation report
                                          ├─ matched  ✔
                                          ├─ flagged  ⚠ (rule + reason)
                                          └─ missing  ✘
```

Run:
```bash
pip install -r requirements.txt
python scripts/reconcile.py --input scripts/sample_data --output reports/
```

Outputs:
- `reconciliation_summary.csv` — per-fund status
- `flagged_issues.csv` — all flags with rule and suggested action
- `master_consolidated.csv` — the validated master workbook

---

## 5. What Made It Work

1. **One template, strict validation** — kills most issues before they compound.
2. **Source links on every number** — audit-friendly and easy to debug.
3. **Severity-based triage** — team knows what to fix first.
4. **Repeatable pipeline** — next quarter is a re-run, not a re-do.

---

*This document is a methodology write-up. No real fund names, figures, or reports are included.*
