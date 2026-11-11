THRESHOLD = 70

TITLE = "Share of species with germination success of 70% or more"
QUESTION = "what share of protocols clear 70% germination success"


def make(tables, plt):
    import pandas as pd
    df = tables["Germination"]
    s = pd.to_numeric(df["germination_success"], errors="coerce")
    total_rows = len(df)
    s = s[(s >= 0) & (s <= 100)]  # same rule as the 'valid percentages' preset
    fig, ax = plt.subplots(figsize=(9, 3.8))
    n = len(s)
    if n == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    clear = int((s >= THRESHOLD).sum())
    below = n - clear
    labels = ["Below %d%%" % THRESHOLD, "%d%% or more" % THRESHOLD]
    counts = [below, clear]
    shares = [c * 100.0 / n for c in counts]
    bars = ax.barh(labels, shares)
    for b, c, p in zip(bars, counts, shares):
        ax.text(min(p + 1, 99), b.get_y() + b.get_height() / 2,
                "%.0f%%  (%d species)" % (p, c), va="center", ha="left")
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of species (%)")
    ax.set_title("Share of species with germination success of %d%% or more: %.0f%%"
                 % (THRESHOLD, shares[1]), loc="left")
    skipped = total_rows - n
    ax.text(0, -0.28, "Based on %d species with a valid %% germination success (0-100)%s."
            % (n, "; %d rows left out (blank, not a number or out of range)" % skipped if skipped else ""),
            transform=ax.transAxes, fontsize=8, va="top")
    fig.tight_layout()
    return fig
