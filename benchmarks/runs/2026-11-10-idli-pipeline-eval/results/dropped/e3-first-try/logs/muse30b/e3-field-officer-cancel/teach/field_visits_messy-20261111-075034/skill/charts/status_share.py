TITLE = "Share of visits by status (% of all visits)"
QUESTION = "share of visits that were Done, Follow-up or Cancelled, overall"

def make(tables, plt):
    df = tables["Visits"]
    col = "status_done_follow_up_cancelled"
    fig, ax = plt.subplots(figsize=(9, 4.5))
    if df is None or len(df) == 0 or col not in df.columns:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    s = df[col].astype("string").str.strip()
    s = s.where(s.notna() & (s != ""), "(blank)")
    known = {"done": "Done", "follow-up": "Follow-up", "cancelled": "Cancelled"}
    s = s.map(lambda v: known.get(str(v).lower(), str(v)[:1].upper() + str(v)[1:].lower()))
    counts = s.value_counts()
    total = counts.sum()
    # keep the top 8, lump the rest
    if len(counts) > 8:
        top = counts.iloc[:8]
        counts = top.copy()
        counts["Others"] = total - top.sum()
    counts = counts.sort_values()
    pct = counts / total * 100
    bars = ax.barh([str(i) for i in pct.index], pct.values)
    for b, p, n in zip(bars, pct.values, counts.values):
        ax.text(b.get_width() + 0.5, b.get_y() + b.get_height() / 2,
                f"{p:.1f}%  ({int(n)} visits)", va="center")
    ax.set_xlim(0, max(pct.max() * 1.25, 1))
    ax.set_xlabel("Share of visits (%)")
    ax.set_title(TITLE, loc="left")
    return fig
