TITLE = "Share of species whose germination success reaches 70% or more"
QUESTION = "what share of protocols clear 70% germination success"
THRESHOLD = 70


def make(tables, plt):
    df = tables["Germination"]
    s = df["germination_success"].dropna()
    s = s[(s >= 0) & (s <= 100)]  # same rule as the "Valid percentages only" preset
    fig, ax = plt.subplots(figsize=(9, 3.6))
    if len(s) == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    n = len(s)
    clear = int((s >= THRESHOLD).sum())
    below = n - clear
    labels = ["Reach %d%% or more" % THRESHOLD, "Below %d%%" % THRESHOLD]
    counts = [clear, below]
    shares = [100.0 * c / n for c in counts]
    y = [1, 0]
    ax.barh(y, shares, height=0.55)
    for yi, sh, c in zip(y, shares, counts):
        ax.text(min(sh + 1, 100), yi, "%.0f%%  (%d of %d species)" % (sh, c, n), va="center", fontsize=10)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlim(0, 125)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("Share of species with a valid germination % (%)")
    ax.set_title(TITLE, loc="left")
    fig.tight_layout()
    return fig
