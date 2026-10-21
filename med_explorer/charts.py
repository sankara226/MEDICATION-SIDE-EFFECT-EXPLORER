"""Matplotlib figures for the notebook and the app.

Each function builds and returns a Figure without showing it, so Gradio
can display it and the notebook can save it.
"""

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

TEAL = "#00808C"
ORANGE = "#F28C28"
GREY = "#9AA0A6"


def make_reactions_chart(df, drug):
    df_sorted = df.sort_values("reports")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(df_sorted["reaction"].str.title(), df_sorted["reports"], color=TEAL)
    ax.set_xlabel("Number of reports")
    ax.set_title(f"Most reported reactions: {drug.lower()}")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    plt.close(fig)
    return fig


def make_sex_chart(comparison, drug):
    if comparison is None or len(comparison) == 0:
        return None

    data = comparison.set_index(comparison["reaction"].str.title())
    data = data[["percent_women", "percent_men"]].iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 6))
    data.plot.barh(ax=ax, color=[TEAL, ORANGE], width=0.8)
    ax.set_xlabel("% of reports mentioning this reaction")
    ax.set_ylabel("")
    ax.set_title(f"Reported reactions by sex: {drug.lower()}")
    ax.legend(["Women", "Men"], frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    plt.close(fig)
    return fig


def make_trend_chart(yearly, drug):
    if yearly is None or len(yearly) == 0:
        return None

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(yearly["year"], yearly["reports"], marker="o", color=TEAL)
    ax.set_xlabel("Year")
    ax.set_ylabel("Number of reports")
    ax.set_title(f"Reports per year: {drug.lower()}")
    ax.grid(alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    plt.close(fig)
    return fig


def make_comparison_chart(yearly_by_drug):
    """One line per drug. `yearly_by_drug` maps a name to its yearly table."""
    fig, ax = plt.subplots(figsize=(10, 5))
    for name, yearly in yearly_by_drug.items():
        ax.plot(yearly["year"], yearly["reports"], marker="o", label=name.lower())
    ax.set_xlabel("Year")
    ax.set_ylabel("Number of reports")
    ax.set_title("Reports per year: comparison")
    ax.legend(frameon=False)
    ax.grid(alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    plt.close(fig)
    return fig


def make_signal_chart(signals, drug, top=15):
    """PRR with its confidence interval, log scale. Flagged signals in teal."""
    if signals is None or len(signals) == 0:
        return None

    data = signals.head(top).iloc[::-1]
    colors = [TEAL if s else GREY for s in data["signal"]]
    labels = data["reaction"].str.title()
    errors = [data["prr"] - data["ci_low"], data["ci_high"] - data["prr"]]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(labels, data["prr"], color=colors)
    ax.errorbar(data["prr"], labels, xerr=errors, fmt="none", ecolor="#333333", capsize=3)
    ax.axvline(1, color="#333333", linewidth=1)
    ax.axvline(2, color=ORANGE, linewidth=1, linestyle="--", label="PRR = 2 threshold")
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:g}"))
    ax.xaxis.set_minor_formatter(ticker.NullFormatter())
    ax.set_xticks([t for t in (1, 2, 3, 5, 10, 20, 50, 100) if t <= data["ci_high"].max() * 1.2])
    ax.set_xlabel("Proportional reporting ratio (log scale, 95% CI)")
    ax.set_title(f"Reactions over-represented for {drug.lower()} vs all other drugs")
    ax.legend(frameon=False, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    plt.close(fig)
    return fig
