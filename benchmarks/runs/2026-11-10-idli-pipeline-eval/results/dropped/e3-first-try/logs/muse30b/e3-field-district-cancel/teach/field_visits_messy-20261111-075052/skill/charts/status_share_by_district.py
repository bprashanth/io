TITLE = "Share of visits by status, by district (% of visits)"
QUESTION = "what share of visits were Done, Follow-up or Cancelled, by district"

def make(tables, plt):
    df = tables["Visits"]
    st, dist = "status_done_follow_up_cancelled", "officer_district"
    fig, ax = plt.subplots(figsize=(9, 5))
    d = df[[dist, st]].dropna()
    if d.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    ct = d.groupby([dist, st]).size().unstack(fill_value=0)
    # keep the taught order first, then any other statuses by size
    order = [c for c in ["Done", "Follow-up", "Cancelled"] if c in ct.columns]
    rest = [c for c in ct.sum().sort_values(ascending=False).index if c not in order]
    cols = order + rest
    if len(cols) > 6:
        ct["Others"] = ct[cols[6:]].sum(axis=1)
        cols = cols[:6] + ["Others"]
    ct = ct[cols]
    totals = ct.sum(axis=1)
    pct = ct.div(totals, axis=0) * 100
    pct = pct.sort_values(cols[0], ascending=True)
    totals = totals.reindex(pct.index)
    left = [0.0] * len(pct)
    for c in cols:
        ax.barh(pct.index, pct[c], left=left, label=str(c))
        for i, (v, l) in enumerate(zip(pct[c], left)):
            if v >= 6:
                ax.text(l + v / 2, i, f"{v:.0f}%", ha="center", va="center", color="white", fontsize=9)
        left = [l + v for l, v in zip(left, pct[c])]
    ax.set_yticks(range(len(pct)))
    ax.set_yticklabels([f"{k} (n={int(totals[k])})" for k in pct.index])
    ax.set_xlim(0, 100)
    ax.set_xlabel("% of visits in the district")
    ax.set_title(TITLE)
    ax.legend(title="Status", ncol=len(cols), loc="upper center", bbox_to_anchor=(0.5, -0.15), frameon=False)
    fig.tight_layout()
    return fig
