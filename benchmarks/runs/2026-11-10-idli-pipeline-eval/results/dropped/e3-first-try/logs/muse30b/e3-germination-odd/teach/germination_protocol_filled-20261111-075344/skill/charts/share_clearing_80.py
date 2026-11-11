TITLE = "Share of protocols clearing 80% germination success (% of species)"
QUESTION = "what share of protocols clear 80% germination success"
THRESHOLD = 80

def make(tables, plt):
    import pandas as pd
    df = list(tables.values())[0] if "Germination" not in tables else tables["Germination"]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    s = pd.to_numeric(df["germination_success"], errors="coerce")
    s = s[(s >= 0) & (s <= 100)]  # valid percentages only, as the skill's preset
    n = len(s)
    if n == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    hit = int((s >= THRESHOLD).sum())
    miss = n - hit
    labels = ["Below %d%%" % THRESHOLD, "%d%% or more" % THRESHOLD]
    counts = [miss, hit]
    pcts = [100.0 * c / n for c in counts]
    bars = ax.barh(labels, pcts, color=["#9aa5b1", "#0072B2"])
    for b, c, p in zip(bars, counts, pcts):
        ax.text(b.get_width() + 1, b.get_y() + b.get_height() / 2,
                "%.0f%%  (%d of %d species)" % (p, c, n), va="center")
    ax.set_xlim(0, 115)
    ax.set_xlabel("Share of species with a valid germination %% (%%)")
    ax.set_title("%.0f%% of protocols reach %d%% germination or more" % (100.0 * hit / n, THRESHOLD), loc="left")
    return fig
