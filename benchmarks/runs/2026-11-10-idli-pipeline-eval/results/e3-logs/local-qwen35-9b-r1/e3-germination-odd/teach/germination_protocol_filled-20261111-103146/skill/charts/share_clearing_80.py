TITLE = "Share of protocols with germination success of 80% or more"
QUESTION = "what share of protocols clear 80% germination success"
THRESHOLD = 80

def make(tables, plt):
    import pandas as pd
    df = tables["Germination"]
    s = pd.to_numeric(df["germination_success"], errors="coerce")
    s = s[(s >= 0) & (s <= 100)]  # valid percentages only, as in the skill's preset
    fig, ax = plt.subplots(figsize=(9, 3.8))
    n = len(s)
    if n == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    hit = int((s >= THRESHOLD).sum())
    miss = n - hit
    labels = [f"{THRESHOLD}% or more", f"Below {THRESHOLD}%"]
    counts = [hit, miss]
    shares = [100 * c / n for c in counts]
    y = [1, 0]
    ax.barh(y, shares, height=0.55)
    for yi, sh, c in zip(y, shares, counts):
        ax.text(sh + 1, yi, f"{sh:.0f}%  ({c} of {n})", va="center")
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlim(0, 115)
    ax.set_xticks(range(0, 101, 20))
    ax.set_xlabel("Share of protocols (%)")
    ax.set_title(TITLE, loc="left")
    fig.text(0.01, 0.01, f"Protocols with a valid % germination success (0-100): {n}", fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    return fig
