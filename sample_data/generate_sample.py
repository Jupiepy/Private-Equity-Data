"""
Generate example reconciliation input workbooks for Private-Equity-Data.

This is a *template* generator: it writes a small set of Excel files into
``sample_data/generated/`` that exercise the reconciliation pipeline. The column
layout is a minimal, self-consistent example (opening / movement / closing
balances per account). Adjust the ``COLUMNS`` / ``SUBFUNDS`` constants to match
your real template before feeding the output to ``reconcile.py``.

Run:
    python sample_data/generate_sample.py

Requires: pandas, openpyxl   (see requirements.txt)
"""
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent / "generated"
OUT.mkdir(exist_ok=True)

COLUMNS = [
    "account",
    "opening_balance",
    "movement_in",
    "move_out",
    "closing_balance",
    "currency",
]

ACCOUNTS = [
    "Cash",
    "Listed Equities",
    "Private Equity",
    "Receivables",
    "Payables",
]


def make_subfund(name: str, seed: int) -> pd.DataFrame:
    rows = []
    for k, acc in enumerate(ACCOUNTS):
        opening = 1_000_000 + seed * 10_000 + k * 50_000
        move_in = (seed + k) * 5_000
        move_out = (seed + k) * 3_000
        closing = opening + move_in - move_out
        rows.append(
            {
                "account": acc,
                "opening_balance": opening,
                "movement_in": move_in,
                "move_out": move_out,
                "closing_balance": closing,
                "currency": "CNY",
            }
        )
    return pd.DataFrame(rows, columns=COLUMNS)


def main():
    for sf in range(1, 4):
        df = make_subfund("Subfund %02d" % sf, sf)
        path = OUT / ("subfund_%02d_example.xlsx" % sf)
        df.to_excel(path, index=False)
        print("wrote", path)


if __name__ == "__main__":
    main()
