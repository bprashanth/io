TITLE = "Share of visits by status, by officer's district (% of visits)"
QUESTION = "what share of visits are Done, Follow-up or Cancelled in each officer district"

def make(tables, plt):
    df = tables["Visits"]
    scol, dcol = "status_done_follow_up_cancelled", "officer_district"
    fig, ax = plt.subplots(figsize=(9, 5))
    if df is None or len(df) == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center"); ax.axis("off"); return fig
    d = df[[scol, dcol]].copy()
    d[scol] = d[scol].fillna("(blank)").astype(str).str.strip().replace("", "(blank)")
    d[dcol] = d[dcol].fillna("No district").astype(str).str.strip().replace("", "No district")
    # keep the 5 most common statuses, group the rest
    top = list(d[scol].value_counts().index[:5])
    d[scol] = d[scol].where(d[scol].isin(top), "Others")
    ct = d.groupby([dcol, scol]).size().unstack(fill_value=0)
    order = [c for c in top if c in ct.columns] + (["Others"] if "Others" in ct.columns else [])
    ct = ct[order]
    totals = ct.sum(axis=1)
    pct = ct.div(totals, axis=0) * 100
    pct = pct.loc[pct[order[0]].sort_values().index]
    totals = totals.loc[pct.index]
    left = [0.0] * len(pct)
    y = range(len(pct))
    for c in order:
        vals = pct[c].values
        ax.barh(list(y), vals, left=left, label=c)
        for i, (v, l) in enumerate(zip(vals, left)):
            if v >= 6:
                ax.text(l + v / 2, i, f"{v:.0f}%", ha="center", va="center", color="white", fontsize=9)
        left = [l + v for l, v in zip(left, vals)]
    ax.set_yticks(list(y))
    ax.set_yticklabels([f"{k} ({int(totals[k])} visits)" for k in pct.index])
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of visits (%)")
    ax.set_ylabel("Officer's district")
    ax.set_title(TITLE)
    ax.legend(title="Status", loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=len(order), frameon=False)
    fig.tight_layout()
    return fig
