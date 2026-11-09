"""Medication Side Effect Explorer: Gradio app.

Run locally:   python app.py
Deploy:        see deploy/README.md (Render).
"""

import gradio as gr

from med_explorer.analysis import (
    compare_by_sex,
    count_reports,
    find_drug,
    get_drug_catalog,
    get_reaction_signals,
    get_reports_by_sex,
    get_top_reactions,
    get_yearly_reports,
)
from med_explorer.charts import (
    make_reactions_chart,
    make_sex_chart,
    make_signal_chart,
    make_trend_chart,
)

# Loaded once at startup for "did you mean" suggestions. If openFDA is down
# the app still works, it just can't suggest spellings.
catalog, _ = get_drug_catalog()

DISCLAIMER = """
---
**About this data:** reports come from the FDA Adverse Event Reporting System (FAERS) via openFDA.
A report means someone took a medication and later experienced a reaction. **It does not prove the medication caused it.**
Report numbers also depend on how widely a drug is used and on media attention.

**This tool is for educational purposes and is not medical advice.**
Never stop or change a medication without talking to your doctor or pharmacist.
"""

SIGNAL_NOTE = """
**How to read this tab.** The proportional reporting ratio (PRR) compares the share of this drug's reports
that mention a reaction with the same share for every other drug. A PRR of 3 means the reaction appears
three times more often, proportionally. Teal bars meet a common screening rule (PRR >= 2, 95% CI above 1,
at least 3 reports). A signal is a reason to look closer, not proof of harm.
"""

EMPTY = (None,) * 6


def analyze(drug_input):
    drug, message = find_drug(drug_input, catalog)
    if drug is None:
        return (message,) + EMPTY

    reactions, error = get_top_reactions(drug)
    if error:
        return (error,) + EMPTY

    total, _ = count_reports(drug)
    yearly, _ = get_yearly_reports(drug)
    by_sex, _ = get_reports_by_sex(drug)
    comparison, _ = compare_by_sex(drug)
    signals, _ = get_reaction_signals(drug)

    lines = [f"## {drug.title()}"]
    if message:
        lines.append(f"*{message}*")
    if total:
        lines.append(f"**Total reports:** {total:,}")
    if yearly is not None and len(yearly) > 0:
        peak = yearly.loc[yearly["reports"].idxmax()]
        lines.append(f"**Peak year:** {int(peak['year'])} ({int(peak['reports']):,} reports)")
    if by_sex is not None:
        shares = ", ".join(f"{row['sex']}: {row['percent']}%" for _, row in by_sex.iterrows())
        lines.append(f"**Reports by sex:** {shares}")
    if signals is not None:
        flagged = signals[signals["signal"]]["reaction"].str.lower().head(5).tolist()
        if flagged:
            lines.append(f"**Strongest signals:** {', '.join(flagged)}")

    signal_table = None
    if signals is not None:
        signal_table = signals[["reaction", "reports", "percent_drug", "percent_others", "prr", "ci_low", "ci_high", "signal"]]

    return (
        "\n\n".join(lines),
        reactions,
        make_reactions_chart(reactions, drug),
        make_sex_chart(comparison, drug),
        make_trend_chart(yearly, drug),
        make_signal_chart(signals, drug),
        signal_table,
    )


with gr.Blocks(title="Medication Side Effect Explorer") as app:
    gr.Markdown("# Medication Side Effect Explorer")
    gr.Markdown(
        "Explore side effects reported to the U.S. FDA for any medication. "
        "Generic and brand names both work (e.g. *sertraline* or *Zoloft*)."
    )

    with gr.Row():
        drug_box = gr.Textbox(label="Medication name", placeholder="e.g. sertraline", scale=4)
        analyze_btn = gr.Button("Analyze", variant="primary", scale=1)

    gr.Examples(examples=["sertraline", "metformin", "ibuprofen", "Zoloft"], inputs=drug_box)

    summary_out = gr.Markdown()

    with gr.Tabs():
        with gr.Tab("Top reactions"):
            reactions_chart = gr.Plot()
            reactions_table = gr.DataFrame()
        with gr.Tab("Women vs Men"):
            sex_chart = gr.Plot()
        with gr.Tab("Trend over time"):
            trend_chart = gr.Plot()
        with gr.Tab("Signals (PRR)"):
            gr.Markdown(SIGNAL_NOTE)
            signal_chart = gr.Plot()
            signal_table = gr.DataFrame()

    gr.Markdown(DISCLAIMER)

    outputs = [summary_out, reactions_table, reactions_chart, sex_chart, trend_chart, signal_chart, signal_table]
    analyze_btn.click(analyze, inputs=drug_box, outputs=outputs)
    drug_box.submit(analyze, inputs=drug_box, outputs=outputs)


if __name__ == "__main__":
    app.launch()
