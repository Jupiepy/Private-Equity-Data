# Reconciliation Rules — Private Equity Data

This document describes the controls that `reconcile.py` is built to check. It is
intended as a reference for reviewers and as a checklist when onboarding a new
fund's data. Rules are grouped by layer; the implementation may cover a subset.

## 1. Balance tie-out (within a period)
For every account row the following must hold:

```
closing_balance = opening_balance + movement_in - move_out
```

A breach is a **blocking** finding: the period cannot be signed off until the
numbers are explained.

## 2. Cross-period continuity
The `closing_balance` of period *N* must equal the `opening_balance` of period
*N+1* for the same account. A mismatch indicates a roll-forward error or a
missed journal entry.

Accounts with **no prior-period data** are flagged as `skipped_no_prior` rather
than failed — they are new positions, not errors, but they still need a human
eye.

## 3. Currency consistency
- Every balance row must carry a valid ISO 4217 `currency` code.
- When a sub-fund is denominated in a base currency, FX conversion must be
  applied with the rate dated to the period end, not the period average.

## 4. Sign and sanity checks
- `movement_in` and `move_out` should be non-negative (direction is a separate
  field, not a negative number).
- Absolute balances should sit within a plausible band for the fund; outliers are
  **flagged** for review, not blocked.

## 5. Status gate (`--fail-on`)
The CLI exposes a severity gate so CI can decide whether to fail:

| Setting | Behaviour |
|---------|-----------|
| `none` | Report everything, never non-zero exit |
| `flagged` | Non-zero exit only on flagged findings |
| `blocking` | Non-zero exit on any blocking finding (default for sign-off) |

## 6. Output
Results are written to `output/`. Each finding records the account, period,
observed vs. expected value, and a stable `status` string so downstream tooling
can trend reconciliation health over time.
