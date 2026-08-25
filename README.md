# Private Equity Post-Investment Data Cleaning Toolkit

## Project Background
During my internship at Hunan Xiangjiang Shengshi Investment Management Co., Ltd., I was responsible for maintaining the semi-annual valuation data for a **government-guided FOF (Fund of Funds)** covering **26 sub-funds and over 200 portfolio companies**. The raw data came from multiple sources (sub-fund manager reports, financial statements, internal valuation models) in inconsistent formats, making it difficult to track performance and identify risks.

## My Role & Contributions
- **Data Consolidation**: Integrated valuation data from 26 sub-funds into a unified Excel-based tracking system, covering metrics such as NAV, contributed capital, distributions, holding value, and fair value adjustments.
- **Data Validation**: Cross-checked sub-fund financial statements against internal valuation models, identifying and flagging discrepancies (e.g., missing financials, classification mismatches between B2/C/D categories) for further review.
- **Variance Analysis**: Tracked holding value changes across semi-annual periods (2025H1 vs. 2024H2), highlighting key drivers such as IPO exits, write-downs, and valuation method changes (e.g., market approach vs. cost approach).
- **Portfolio Classification**: Assisted in reclassifying projects based on exit uncertainty and operational risks (A/B/C/D categories), directly impacting fair value reporting.

## Key Data Points I Handled
- 26 sub-funds with total contributed capital of ~RMB 1.89 billion
- 200+ underlying portfolio companies across sectors (semiconductors, healthcare, consumer, etc.)
- Valuation adjustments tracked over multiple periods (2022–2026)
- Identified 10+ projects with significant valuation write-downs (D-class) due to operational distress or legal issues

## Technical Tools Used
- Excel (Power Query, pivot tables, formula-based variance checks)
- Basic Python (Pandas) for data cleaning and consistency checks on exported Excel files
- Version control via GitHub to track data dictionary updates

## What This Repo Contains
- `PE_PostInvestment_Data_Dictionary.xlsx` – Field definitions for the valuation master table
- `Sample_Data_Processing_Log.md` – Anonymized log of data issues identified and resolved
- `Valuation_Summary_2025H1.csv` – Anonymized sample of aggregated valuation data (no sensitive info)

## Key Takeaway
This experience taught me how to **turn messy financial data into actionable insights** for investment decision-making — a skill I believe is essential for Fintech, where data quality is the foundation of every model.# Private-Equity-Data
Automated ETL scripts using Pandas for standardizing post-investment financial reports from multi-manager PE funds, addressing real-world data heterogeneity challenges.
