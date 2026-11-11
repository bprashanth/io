TITLE = "Share of species clearing 70% germination success"
QUESTION = "what share of protocols clear 70% germination success"
THRESHOLD = 70


def make(tables, plt):
    import pandas as pd
    df = tables["Germination"]
    s = pd.to_numeric(df["germination_success"], errors="coerce")
    valid = s[(s >= 0) & (s <= 100)]
    excluded = int(len(s) - len(valid))
    fig, ax = plt.subplots(figsize=(9, 3.2))
    n = len(valid)
    if n == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    clear = int((valid >= THRESHOLD).sum())
    below = n - clear
    pc, pb = 100 * clear / n, 100 * below / n
    ax.barh([0], [pc], color="#0072B2", label=f"{THRESHOLD}% or more")
    ax.barh([0], [pb], left=[pc], color="#D9D9D9", label=f"Below {THRESHOLD}%")
    if pc > 4:
        ax.text(pc / 2, 0, f"{pc:.0f}%\n{clear} species", ha="center", va="center", color="white", fontsize=12, fontweight="bold")
    if pb > 4:
        ax.text(pc + pb / 2, 0, f"{pb:.0f}%\n{below} species", ha="center", va="center", color="#333333", fontsize=12, fontweight="bold")
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.6, 0.6)
    ax.set_yticks([])
    ax.set_xlabel("Share of species with a valid % germination success (%)")
    ax.set_title(TITLE, loc="left")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.3), ncol=2, frameon=False)
    note = f"Based on {n} species with a valid percentage (0-100)."
    if excluded:
        note += f" {excluded} left out (blank or impossible value)."
    fig.text(0.01, 0.01, note, fontsize=9, color="#555555")
    fig.subplots_adjust(bottom=0.4)
    return fig
