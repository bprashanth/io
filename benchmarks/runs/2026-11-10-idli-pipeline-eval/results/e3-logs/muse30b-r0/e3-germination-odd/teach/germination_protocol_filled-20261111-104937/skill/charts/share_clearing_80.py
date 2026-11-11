TITLE = "Share of protocols with germination success of 80% or more"
QUESTION = "what share of protocols clear 80% germination success"
THRESHOLD = 80


def make(tables, plt):
    df = tables["Germination"]
    s = df["germination_success"]
    s = s[(s >= 0) & (s <= 100)]  # valid percentages only; blanks and bad values left out
    fig, ax = plt.subplots(figsize=(9, 3.6))
    n = len(s)
    if n == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    k = int((s >= THRESHOLD).sum())
    parts = [(f"{THRESHOLD}% or more", k), (f"Below {THRESHOLD}%", n - k)]
    left = 0.0
    colors = ["C0", "#c8c8c8"]
    for (label, c), col in zip(parts, colors):
        pct = 100.0 * c / n
        ax.barh([0], [pct], left=left, color=col, height=0.5)
        if pct > 0:
            ax.text(left + pct / 2, 0, f"{label}\n{c} of {n} ({pct:.0f}%)", ha="center",
                    va="center", color="white" if col == "C0" else "black", fontsize=10)
        left += pct
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.5, 0.5)
    ax.set_yticks([])
    ax.set_xlabel("% of protocols with a valid germination success value")
    ax.set_title(TITLE, loc="left")
    return fig
