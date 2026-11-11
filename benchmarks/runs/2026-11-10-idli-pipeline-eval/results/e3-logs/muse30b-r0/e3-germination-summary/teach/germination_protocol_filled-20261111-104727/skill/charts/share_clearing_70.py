TITLE = "Share of protocols with at least 70% germination success"
QUESTION = "what share of protocols clear 70% germination success"
THRESHOLD = 70


def make(tables, plt):
    import pandas as pd
    df = tables["Germination"]
    s = pd.to_numeric(df["germination_success"], errors="coerce")
    total_rows = len(s)
    s = s[(s >= 0) & (s <= 100)]  # valid percentages only (same rule as the skill's preset)
    fig, ax = plt.subplots(figsize=(9, 3.6))
    n = len(s)
    if n == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    clear = int((s >= THRESHOLD).sum())
    below = n - clear
    labels = ["Below %d%%" % THRESHOLD, "%d%% or more" % THRESHOLD]
    counts = [below, clear]
    shares = [c / n * 100 for c in counts]
    bars = ax.barh(labels, shares)
    for b, c, sh in zip(bars, counts, shares):
        ax.text(b.get_width() + 1, b.get_y() + b.get_height() / 2,
                "%.0f%%  (%d protocols)" % (sh, c), va="center")
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of protocols (%)")
    ax.set_title(TITLE, loc="left")
    skipped = total_rows - n
    ax.text(0, -0.32, "Based on %d protocols with a valid %% germination success (0-100); %d left out (blank or invalid)."
            % (n, skipped), transform=ax.transAxes, fontsize=8, va="top")
    fig.tight_layout()
    return fig
