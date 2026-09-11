"""
FOF Reconciliation Visualization Dashboard.

Generates static charts (matplotlib/seaborn) for reconciliation results.

Usage:
    from visualization import plot_reconciliation_dashboard
    plot_reconciliation_dashboard(df, save_dir="reports/")
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from pathlib import Path

# Set style
sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (12, 8)
plt.rcParams["font.size"] = 10


def plot_status_pie(df: pd.DataFrame, ax=None) -> None:
    """Pie chart of matched / warning / flagged / blocking / missing."""
    status_counts = df["status"].value_counts()
    colors = {
        "matched": "#2ecc71",
        "warning": "#f39c12",
        "flagged": "#e74c3c",
        "blocking": "#8e44ad",
        "missing": "#95a5a6",
    }
    color_list = [colors.get(s, "#3498db") for s in status_counts.index]
    
    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 6))
    
    wedges, texts, autotexts = ax.pie(
        status_counts.values,
        labels=status_counts.index,
        autopct="%1.1f%%",
        colors=color_list,
        startangle=90,
        explode=[0.02] * len(status_counts),
    )
    ax.set_title("Reconciliation Status Distribution", fontsize=14, fontweight="bold")


def plot_fair_value_by_fund(df: pd.DataFrame, ax=None) -> None:
    """Bar chart of fair value per fund, colored by status."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(14, 5))
    
    colors = {
        "matched": "#2ecc71",
        "warning": "#f39c12",
        "flagged": "#e74c3c",
        "blocking": "#8e44ad",
        "missing": "#95a5a6",
    }
    
    df_plot = df.sort_values("fair_value", na_position="last").copy()
    df_plot["color"] = df_plot["status"].map(colors)
    
    bars = ax.bar(
        df_plot["fund_id"],
        df_plot["fair_value"] / 1e6,
        color=df_plot["color"],
        edgecolor="black",
        linewidth=0.3,
    )
    ax.set_xlabel("Fund ID", fontsize=11)
    ax.set_ylabel("Fair Value (RMB Million)", fontsize=11)
    ax.set_title("Fair Value by Sub-Fund (colored by status)", fontsize=14, fontweight="bold")
    ax.tick_params(axis="x", rotation=45)
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=colors[s], label=s) for s in colors if s in df["status"].values]
    ax.legend(handles=legend_elements, loc="upper right")
    
    # Highlight zero / missing
    for bar, fv in zip(bars, df_plot["fair_value"]):
        if pd.isna(fv) or fv == 0:
            ax.annotate("⚠", xy=(bar.get_x() + bar.get_width()/2, 0), 
                       ha="center", va="bottom", fontsize=14, color="red")


def plot_check_heatmap(df: pd.DataFrame, ax=None) -> None:
    """Heatmap showing which checks passed/failed per fund."""
    check_cols = [c for c in df.columns if c.startswith("check_")]
    if not check_cols:
        return
    
    # Convert to binary: 1 = pass, 0 = fail, 0.5 = not checked
    def _binary(val):
        if pd.isna(val):
            return 0.5
        # Any "skipped_*" status means the rule never ran, so it is neither a
        # pass nor a fail -- paint it neutral instead of red.
        if str(val).startswith("skipped"):
            return 0.5
        return 1.0 if val == "pass" else 0.0
    
    # DataFrame.applymap is deprecated in pandas 2.1 and removed in 3.0;
    # Series.map keeps this working on both the old and the new API.
    heat_data = df[["fund_id"] + check_cols].set_index("fund_id").apply(lambda col: col.map(_binary))
    
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 8))
    
    cmap = sns.color_palette("RdYlGn", as_cmap=True)
    sns.heatmap(
        heat_data,
        cmap=cmap,
        vmin=0, vmax=1,
        linewidths=0.5,
        cbar_kws={"label": "Pass (1) / Skip (0.5) / Fail (0)"},
        ax=ax,
    )
    ax.set_title("Validation Check Results per Fund", fontsize=14, fontweight="bold")
    ax.set_xlabel("Validation Check", fontsize=11)
    ax.set_ylabel("Fund ID", fontsize=11)
    
    # Rename x labels for readability
    labels = [c.replace("check_", "").replace("_", " ").title() for c in check_cols]
    ax.set_xticklabels(labels, rotation=45, ha="right")


def plot_growth_distribution(df: pd.DataFrame, ax=None) -> None:
    """Histogram of quarter-over-quarter growth rates."""
    if "growth_rate" not in df.columns or df["growth_rate"].isna().all():
        if ax:
            ax.text(0.5, 0.5, "No historical data available", ha="center", va="center", transform=ax.transAxes)
            ax.set_title("Cross-Quarter Growth Distribution")
        return
    
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 5))
    
    growth = df["growth_rate"].dropna()
    ax.hist(growth * 100, bins=15, color="steelblue", edgecolor="black", alpha=0.7)
    ax.axvline(50, color="red", linestyle="--", linewidth=2, label="Flag threshold (+50%)")
    ax.axvline(-50, color="red", linestyle="--", linewidth=2, label="Flag threshold (-50%)")
    ax.set_xlabel("QoQ Growth Rate (%)", fontsize=11)
    ax.set_ylabel("Number of Funds", fontsize=11)
    ax.set_title("Cross-Quarter Fair Value Growth Distribution", fontsize=14, fontweight="bold")
    ax.legend()
    
    # Annotate extreme values
    extreme = df[df["check_cross_quarter"] == "fail_extreme_growth"]
    for _, row in extreme.iterrows():
        ax.annotate(
            row["fund_id"],
            xy=(row["growth_rate"] * 100, 0.5),
            xytext=(row["growth_rate"] * 100, 1.5),
            arrowprops=dict(arrowstyle="->", color="red"),
            color="red", fontweight="bold",
        )


def plot_summary_metrics(df: pd.DataFrame, ax=None) -> None:
    """Text-based summary metrics panel."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 4))
    
    total_fv = df["fair_value"].sum()
    matched_fv = df[df["status"] == "matched"]["fair_value"].sum()
    n_flagged = len(df[df["status"].isin(["flagged", "blocking", "missing"])])
    
    metrics = [
        f"Total Funds: {len(df)}",
        f"Matched: {len(df[df['status'] == 'matched'])}",
        f"Flagged/Blocking/Missing: {n_flagged}",
        f"Total Fair Value: ¥{total_fv/1e6:.1f}M",
        f"Clean Fair Value: ¥{matched_fv/1e6:.1f}M",
        f"Flag Rate: {n_flagged/len(df)*100:.1f}%",
    ]
    
    ax.axis("off")
    ax.text(0.1, 0.9, "\n".join(metrics), transform=ax.transAxes,
            fontsize=13, verticalalignment="top", family="monospace",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.3))
    ax.set_title("Key Metrics", fontsize=14, fontweight="bold")


def plot_reconciliation_dashboard(df: pd.DataFrame, save_dir: Path = Path("reports")) -> Path:
    """Generate a complete 2x3 dashboard and save to file."""
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    
    fig = plt.figure(figsize=(18, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)
    
    ax_pie = fig.add_subplot(gs[0, 0])
    ax_metrics = fig.add_subplot(gs[0, 1])
    ax_growth = fig.add_subplot(gs[0, 2])
    ax_fv = fig.add_subplot(gs[1, :])
    ax_heat = fig.add_subplot(gs[2, :])
    
    plot_status_pie(df, ax=ax_pie)
    plot_summary_metrics(df, ax=ax_metrics)
    plot_growth_distribution(df, ax=ax_growth)
    plot_fair_value_by_fund(df, ax=ax_fv)
    plot_check_heatmap(df, ax=ax_heat)
    
    fig.suptitle("FOF Valuation Reconciliation Dashboard", fontsize=18, fontweight="bold", y=0.98)
    
    out_path = save_dir / "reconciliation_dashboard.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    
    print(f"📊 Dashboard saved to: {out_path}")
    return out_path


if __name__ == "__main__":
    # Demo: load a reconciliation result and plot
    import sys
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
        df = pd.read_csv(csv_path)
        plot_reconciliation_dashboard(df)
    else:
        print("Usage: python visualization.py <path_to_master_consolidated.csv>")
