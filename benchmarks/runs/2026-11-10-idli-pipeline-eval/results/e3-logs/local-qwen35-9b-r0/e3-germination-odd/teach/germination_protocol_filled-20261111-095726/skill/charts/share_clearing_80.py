TITLE = "Share of protocols with at least 80% germination success (% of species)"
QUESTION = "what share of protocols clear 80% germination success?"
THRESHOLD = 80

def make(tables, plt):
    df = tables["Germination"]
    s = df["germination_success"]
    valid = s[(s >= 0) & (s <= 100)].dropna()
    skipped = len(df) - len(valid)
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.set_title(TITLE, loc="left")
    if len(valid) == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    n_hi = int((valid >= THRESHOLD).sum())
    n_lo = len(valid) - n_hi
    p_hi = 100 * n_hi / len(valid)
    p_lo = 100 - p_hi
    ax.barh([0], [p_hi], height=0.5, label=f"{THRESHOLD}% or more")
    ax.barh([0], [p_lo], left=[p_hi], height=0.5, color="#c9ccd1", label=f"Below {THRESHOLD}%")
    for x0, w, n in ((0, p_hi, n_hi), (p_hi, p_lo, n_lo)):
        if w >= 6:
            ax.text(x0 + w / 2, 0, f"{w:.0f}%\n({n} species)", ha="center", va="center", fontsize=11)
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.5, 0.5)
    ax.set_yticks([])
    ax.set_xlabel("% of species with a valid germination figure")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.28), ncol=2, frameon=False)
    if skipped:
        ax.text(0, 1.02, f"{skipped} species left out: success figure missing or not between 0 and 100",
                transform=ax.transAxes, fontsize=9, va="bottom")
    ax.spines["left"].set_visible(False)
    fig.tight_layout()
    return fig
