TITLE = "Share of trees with canopy, by size class (%)"
QUESTION = "share of trees in each size class that have canopy"

BINS = [0, 10, 20, 30, 50, float("inf")]
LABELS = ["< 10 cm", "10-20 cm", "20-30 cm", "30-50 cm", "50+ cm"]


def make(tables, plt):
    import pandas as pd
    df = tables["Raw 10x10m Data"]
    dbh = pd.to_numeric(df["dbh_1_cm"], errors="coerce")
    c = df["canopy_y_n"].astype(str).str.strip().str.lower()
    yes = c.isin(["y", "yes"])
    known = yes | c.isin(["n", "no"])
    d = pd.DataFrame({"dbh": dbh, "yes": yes})[dbh.notna() & known]
    fig, ax = plt.subplots(figsize=(9, 5))
    if d.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    d["cls"] = pd.cut(d["dbh"], BINS, labels=LABELS, right=False)
    g = d.groupby("cls", observed=False)["yes"].agg(["mean", "count"]).reindex(LABELS)
    g = g[g["count"] > 0]
    pos = list(range(len(g)))
    ax.barh(pos, g["mean"] * 100)
    ax.set_yticks(pos)
    ax.set_yticklabels(g.index)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    for p, (m, n) in zip(pos, zip(g["mean"], g["count"])):
        ax.text(m * 100 + 1, p, f"{m*100:.0f}%  (n={int(n)})", va="center")
    ax.set_xlabel("Trees with canopy (% of trees in the size class)")
    ax.set_ylabel("Size class (DBH 1)")
    ax.set_title(TITLE)
    return fig
