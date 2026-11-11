TITLE = "Share of households with more than 1 acre of land, by ward (%)"
QUESTION = "what share of households have more than one acre, by ward"


def make(tables, plt):
    df = tables["Households"][["ward", "land_acres"]].copy()
    df = df.dropna(subset=["ward", "land_acres"])
    fig, ax = plt.subplots(figsize=(9, 5))
    if df.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    df["over"] = df["land_acres"] > 1
    g = df.groupby("ward")["over"].agg(["mean", "sum", "count"]).sort_index(ascending=False)
    pct = g["mean"] * 100
    labels = [("Ward %g" % w) for w in g.index]
    bars = ax.barh(labels, pct.values)
    for b, p, n, c in zip(bars, pct.values, g["sum"].values, g["count"].values):
        ax.text(b.get_width() + 1, b.get_y() + b.get_height() / 2,
                "%.0f%%  (%d of %d)" % (p, n, c), va="center")
    ax.set_xlim(0, 100 if pct.max() < 80 else 115)
    ax.set_xlabel("Households with more than 1 acre (% of households in the ward)")
    ax.set_title(TITLE, loc="left")
    return fig
