TITLE = "Share of trees with canopy, by size class (%)"
QUESTION = "what share of trees in each size class have canopy"


def make(tables, plt):
    df = tables["Raw 10x10m Data"].copy()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    order = ["Small", "Medium", "Large"]
    labels = {"Small": "Small (under 10 cm)", "Medium": "Medium (10 to 30 cm)", "Large": "Large (over 30 cm)"}

    def no_data(msg="No data"):
        ax.text(0.5, 0.5, msg, ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig

    if df is None or len(df) == 0 or "dbh_1_cm" not in df.columns or "canopy_y_n" not in df.columns:
        return no_data()

    dbh = df["dbh_1_cm"]
    size = dbh.apply(lambda v: None if v != v or v is None else ("Small" if v < 10 else ("Medium" if v <= 30 else "Large")))
    c = df["canopy_y_n"].astype(str).str.strip().str.lower()
    has = c.isin(["y", "yes"])
    known = c.isin(["y", "yes", "n", "no"])
    d = df.assign(size=size, has=has)[known & size.notna()]
    if len(d) == 0:
        return no_data("No trees with a size and a Y/N canopy answer")

    g = d.groupby("size")["has"].agg(["sum", "count"]).reindex(order)
    g = g.dropna()
    pct = g["sum"] / g["count"] * 100
    ypos = list(range(len(g)))[::-1]
    ax.barh(ypos, pct.values)
    for y, p, n, k in zip(ypos, pct.values, g["count"].values, g["sum"].values):
        ax.text(p + 1.5, y, f"{p:.0f}%  ({int(k)} of {int(n)} trees)", va="center")
    ax.set_yticks(ypos)
    ax.set_yticklabels([labels[i] for i in g.index])
    ax.set_xlim(0, 118)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("Trees with canopy (% of trees in the size class)")
    ax.set_title(TITLE, loc="left")
    return fig
