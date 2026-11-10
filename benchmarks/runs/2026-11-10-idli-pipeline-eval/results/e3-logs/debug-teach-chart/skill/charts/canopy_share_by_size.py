TITLE = "Share of trees with canopy, by size class (%)"
QUESTION = "what share of trees in each size class have canopy"

def make(tables, plt):
    import pandas as pd
    df = tables["Raw 10x10m Data"]
    fig, ax = plt.subplots(figsize=(8, 4))
    d = df[df["canopy_y_n"].isin(["Y", "N"]) & df["dbh_1_cm"].notna()].copy()
    if d.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    d["size"] = pd.cut(d["dbh_1_cm"], [-float("inf"), 10, 30, float("inf")],
                       labels=["Small (<10 cm)", "Medium (10-30 cm)", "Large (>30 cm)"], right=False)
    # Medium includes exactly 30, Large is over 30
    d.loc[d["dbh_1_cm"] == 30, "size"] = "Medium (10-30 cm)"
    g = d.groupby("size", observed=True)["canopy_y_n"].agg(n="size", c=lambda s: (s == "Y").sum())
    g["share"] = 100.0 * g["c"] / g["n"]
    g = g.iloc[::-1]
    ax.barh([str(i) for i in g.index], g["share"])
    for i, (sh, n) in enumerate(zip(g["share"], g["n"])):
        ax.text(sh + 1, i, f"{sh:.0f}%  (n={int(n)})", va="center")
    ax.set_xlim(0, 115)
    ax.set_xlabel("Trees with canopy (% of trees in the size class)")
    ax.set_ylabel("Size class (DBH 1)")
    ax.set_title(TITLE)
    fig.tight_layout()
    return fig
