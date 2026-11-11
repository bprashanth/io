TITLE = "Share of trees with canopy, by size class (%)"
QUESTION = "what share of trees in each size class have canopy"

def make(tables, plt):
    df = tables["Raw 10x10m Data"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    d = df[["dbh_1_cm", "canopy_y_n"]].copy()
    d = d[d["dbh_1_cm"].notna() & d["canopy_y_n"].isin(["Y", "N"])]
    if d.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    def cls(x):
        return "Small (<10 cm)" if x < 10 else ("Medium (10-30 cm)" if x <= 30 else "Large (>30 cm)")
    d["size"] = d["dbh_1_cm"].map(cls)
    order = ["Small (<10 cm)", "Medium (10-30 cm)", "Large (>30 cm)"]
    g = d.groupby("size")["canopy_y_n"].agg(n="size", c=lambda s: (s == "Y").sum())
    g = g.reindex(order).dropna()
    share = 100.0 * g["c"] / g["n"]
    y = list(range(len(g)))
    ax.barh(y, share.values)
    ax.set_yticks(y)
    ax.set_yticklabels(g.index)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    for i, (s, n) in enumerate(zip(share.values, g["n"].values)):
        ax.text(s + 1, i, f"{s:.0f}%  ({int(n)} trees)", va="center")
    ax.set_xlabel("Trees with canopy (% of trees in the size class; DBH 1 and canopy Y/N recorded)")
    ax.set_title(TITLE, loc="left")
    fig.tight_layout()
    return fig
