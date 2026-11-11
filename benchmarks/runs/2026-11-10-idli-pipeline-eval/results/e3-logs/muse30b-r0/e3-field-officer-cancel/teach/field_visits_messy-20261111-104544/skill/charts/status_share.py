TITLE = "Share of visits by status (all visits)"
QUESTION = "what share of visits were Done, Follow-up or Cancelled overall"

def make(tables, plt):
    df = tables["Visits"]
    col = "status_done_follow_up_cancelled"
    fig, ax = plt.subplots(figsize=(9, 5))
    if df is None or len(df) == 0 or col not in df.columns:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    s = df[col].astype(str).str.strip()
    s = s.where(df[col].notna() & (s != "") & (s.str.lower() != "nan"), "(blank)")
    counts = s.value_counts()
    top = 7
    if len(counts) > top:
        others = counts.iloc[top:].sum()
        counts = counts.iloc[:top]
        counts["Others"] = others
    total = counts.sum()
    share = counts / total * 100
    share = share.iloc[::-1]
    ax.barh(share.index, share.values)
    for i, (v, n) in enumerate(zip(share.values, counts.iloc[::-1].values)):
        ax.text(v + 0.5, i, f"{v:.1f}%  ({int(n)} visits)", va="center")
    ax.set_xlim(0, max(share.values) * 1.3)
    ax.set_xlabel("Share of visits (%)")
    ax.set_title(TITLE)
    return fig
