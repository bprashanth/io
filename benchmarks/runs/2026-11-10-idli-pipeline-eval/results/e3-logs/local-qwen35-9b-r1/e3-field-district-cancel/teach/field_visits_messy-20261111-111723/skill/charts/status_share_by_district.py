TITLE = "Share of visits by status, per district (%)"
QUESTION = "what share of visits were each status, by district"

def make(tables, plt):
    import textwrap
    df = tables["Visits"]
    scol, dcol = "status_done_follow_up_cancelled", "officer_district"
    d = df[[scol, dcol]].copy()
    d[scol] = d[scol].astype("string").str.strip()
    d[dcol] = d[dcol].astype("string").str.strip()
    d = d[d[scol].notna() & (d[scol] != "") & d[dcol].notna() & (d[dcol] != "")]
    fig, ax = plt.subplots(figsize=(9, 5))
    if d.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    ct = d.groupby([dcol, scol]).size().unstack(fill_value=0)
    # keep the 6 most common statuses, group the rest
    order = ct.sum().sort_values(ascending=False).index.tolist()
    if len(order) > 6:
        keep = order[:6]
        ct["Others"] = ct[[c for c in order[6:]]].sum(axis=1)
        ct = ct[keep + ["Others"]]
    else:
        ct = ct[order]
    ct = ct.sort_index()
    pct = ct.div(ct.sum(axis=1), axis=0) * 100
    left = None
    import numpy as np
    left = np.zeros(len(pct))
    ypos = np.arange(len(pct))
    for col in pct.columns:
        vals = pct[col].values
        ax.barh(ypos, vals, left=left, label=textwrap.shorten(str(col), 40), height=0.6)
        for y, l, v in zip(ypos, left, vals):
            if v >= 6:
                ax.text(l + v / 2, y, f"{v:.0f}%", ha="center", va="center", color="white", fontsize=9)
        left = left + vals
    ax.set_yticks(ypos)
    ax.set_yticklabels([str(i) for i in pct.index])
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of the district's visits (%)")
    ax.set_title(TITLE, loc="left")
    ax.legend(title="Status", loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=3, frameon=False)
    fig.tight_layout()
    return fig
