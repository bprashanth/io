TITLE = "Share of trees with canopy, by size class (%)"
QUESTION = "share of trees in each size class that have canopy"

def make(tables, plt):
    import pandas as pd
    df = tables["Raw 10x10m Data"]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    d = df[["dbh_1_cm", "canopy_y_n"]].copy()
    d["dbh"] = pd.to_numeric(d["dbh_1_cm"], errors="coerce")
    d = d[d["dbh"].notna() & d["canopy_y_n"].isin(["Y", "N"])]
    if d.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    d["size"] = pd.cut(d["dbh"], [-float("inf"), 10, 30, float("inf")], right=False,
                       labels=["Small (<10 cm)", "Medium (10-30 cm)", "Large (>30 cm)"])
    # Medium includes exactly 30 cm, as in the form
    d.loc[d["dbh"] == 30, "size"] = "Medium (10-30 cm)"
    g = d.groupby("size", observed=False)["canopy_y_n"].agg(n="size", y=lambda s: (s == "Y").sum())
    g["pct"] = 100.0 * g["y"] / g["n"].where(g["n"] > 0)
    labels = list(g.index)[::-1]
    pct = g["pct"][::-1].fillna(0).tolist()
    ns = g["n"][::-1].tolist()
    ax.barh(labels, pct)
    for i, (p, n) in enumerate(zip(pct, ns)):
        txt = f"{p:.0f}%  (n = {n})" if n else "no trees"
        ax.text(p + 1, i, txt, va="center")
    ax.set_xlim(0, 115)
    ax.set_xlabel("Trees with canopy (% of trees in size class)")
    ax.set_ylabel("Size class (DBH 1)")
    ax.set_title(TITLE)
    fig.tight_layout()
    return fig
