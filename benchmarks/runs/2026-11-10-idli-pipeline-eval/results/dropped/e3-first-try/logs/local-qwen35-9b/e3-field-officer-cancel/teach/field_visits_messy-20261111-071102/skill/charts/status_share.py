import textwrap

TITLE = "Share of visits by status (% of all visits)"
QUESTION = "what share of visits were in each status, overall"


def make(tables, plt):
    df = tables["Visits"]
    col = "status_done_follow_up_cancelled"
    fig, ax = plt.subplots(figsize=(9, 5))
    if df is None or len(df) == 0 or col not in df.columns:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    s = df[col].astype("string").str.strip().str.lower()
    s = s.fillna("(blank)").replace("", "(blank)")
    counts = s.value_counts()
    # keep original-looking labels: capitalise first letter
    counts.index = [str(i)[:1].upper() + str(i)[1:] for i in counts.index]
    counts = counts.groupby(level=0).sum().sort_values(ascending=False)
    top_n = 8
    if len(counts) > top_n:
        others = counts.iloc[top_n:].sum()
        counts = counts.iloc[:top_n]
        counts["Others"] = others
    total = counts.sum()
    share = counts / total * 100
    share = share.iloc[::-1]
    cnt = counts.iloc[::-1]
    labels = ["\n".join(textwrap.wrap(str(i), 40)) for i in share.index]
    bars = ax.barh(labels, share.values)
    for b, p, n in zip(bars, share.values, cnt.values):
        ax.text(b.get_width() + max(share.max() * 0.01, 0.2), b.get_y() + b.get_height() / 2,
                f"{p:.1f}%  ({int(n)} visits)", va="center")
    ax.set_xlim(0, share.max() * 1.3)
    ax.set_xlabel(f"Share of all {int(total)} visits (%)")
    ax.set_ylabel("Status")
    ax.set_title(TITLE)
    fig.tight_layout()
    return fig
