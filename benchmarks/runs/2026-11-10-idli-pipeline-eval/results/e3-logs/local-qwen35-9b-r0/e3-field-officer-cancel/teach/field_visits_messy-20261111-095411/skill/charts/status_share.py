import pandas as pd

TITLE = "Share of visits by status (% of all visits)"
QUESTION = "what share of visits were Done, Follow-up or Cancelled overall"

def make(tables, plt):
    df = tables["Visits"]
    col = "status_done_follow_up_cancelled"
    fig, ax = plt.subplots(figsize=(9, 5))
    s = df[col].astype("string").str.strip().fillna("").replace("", "(blank)")
    if len(s) == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    counts = s.value_counts()
    if len(counts) > 8:
        counts = pd.concat([counts.iloc[:7], pd.Series({"Others": counts.iloc[7:].sum()})])
    total = counts.sum()
    share = (counts / total * 100).sort_values()
    bars = ax.barh(share.index.astype(str), share.values)
    for b, v, n in zip(bars, share.values, counts[share.index].values):
        ax.text(b.get_width() + 0.5, b.get_y() + b.get_height() / 2,
                f"{v:.1f}% ({int(n)} visits)", va="center")
    ax.set_xlim(0, max(share.values) * 1.25)
    ax.set_xlabel("Share of all visits (%)")
    ax.set_title(TITLE)
    fig.tight_layout()
    return fig
