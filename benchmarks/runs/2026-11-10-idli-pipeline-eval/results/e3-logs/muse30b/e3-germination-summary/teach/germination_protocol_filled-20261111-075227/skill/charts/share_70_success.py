TITLE = "Share of protocols with at least 70% germination success"
QUESTION = "what share of protocols achieve at least 70% germination success"

def make(tables, plt):
    import pandas as pd
    df = next(iter(tables.values())) if "Germination" not in tables else tables["Germination"]
    s = pd.to_numeric(df["germination_success"], errors="coerce")
    valid = s[(s >= 0) & (s <= 100)]
    excluded = len(s) - len(valid)
    fig, ax = plt.subplots(figsize=(9, 3.8))
    n = len(valid)
    if n == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    hit = int((valid >= 70).sum())
    low = n - hit
    labels = ["Below 70%", "70% or more"]
    vals = [low / n * 100, hit / n * 100]
    counts = [low, hit]
    bars = ax.barh(labels, vals)
    for b, v, c in zip(bars, vals, counts):
        ax.text(v + 1, b.get_y() + b.get_height() / 2, f"{v:.0f}%  ({c} of {n})", va="center")
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of protocols (%)")
    ax.set_title(TITLE, loc="left")
    note = f"Based on {n} protocols with a valid % germination success (0-100)."
    if excluded:
        note += f" {excluded} left out (blank, not a number or outside 0-100)."
    fig.text(0.01, 0.01, note, fontsize=8, ha="left")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    return fig
