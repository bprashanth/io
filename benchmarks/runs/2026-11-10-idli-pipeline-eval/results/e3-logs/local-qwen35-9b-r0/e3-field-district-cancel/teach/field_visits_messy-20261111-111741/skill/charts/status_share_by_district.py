TITLE = "Share of visits by status, per officer's district (% of visits)"
QUESTION = "what share of visits were Done / Follow-up / Cancelled by district"

def make(tables, plt):
    df = tables["Visits"]
    st, dc = "status_done_follow_up_cancelled", "officer_district"
    fig, ax = plt.subplots(figsize=(9, 5))
    d = df[[st, dc]].copy()
    d[st] = d[st].astype("string").str.strip()
    d = d[d[st].notna() & (d[st] != "")]
    d[dc] = d[dc].astype("string").str.strip().fillna("Unknown district")
    d.loc[d[dc] == "", dc] = "Unknown district"
    if d.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    counts = d.groupby([dc, st]).size().unstack(fill_value=0)
    order = [s for s in ["Done", "Follow-up", "Cancelled"] if s in counts.columns]
    order += [s for s in counts.columns if s not in order]
    counts = counts[order]
    pct = counts.div(counts.sum(axis=1), axis=0) * 100
    pct = pct.sort_index(ascending=False)
    n = counts.sum(axis=1).reindex(pct.index)
    left = pct.iloc[:, 0] * 0
    for s in order:
        ax.barh(pct.index, pct[s], left=left, label=s)
        for y, (l, v) in enumerate(zip(left, pct[s])):
            if v >= 6:
                ax.text(l + v / 2, y, f"{v:.0f}%", ha="center", va="center", color="white", fontsize=9)
        left = left + pct[s]
    ax.set_yticks(range(len(pct.index)))
    ax.set_yticklabels([f"{i} (n={int(n[i])})" for i in pct.index])
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of visits (%)")
    ax.set_title(TITLE)
    ax.legend(title="Status", ncol=len(order), loc="upper center", bbox_to_anchor=(0.5, -0.15), frameon=False)
    fig.tight_layout()
    return fig
