TITLE = "Share of households with more than 1 acre of land, by ward (%)"
QUESTION = "what share of households have more than one acre, by ward"


def make(tables, plt):
    df = tables["Households"]
    fig, ax = plt.subplots(figsize=(9, 5))
    d = df[["ward", "land_acres"]].dropna()
    if len(d) == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    d = d.assign(over=d["land_acres"] > 1)
    g = d.groupby("ward").agg(n=("over", "size"), k=("over", "sum")).reset_index()
    g["pct"] = 100.0 * g["k"] / g["n"]
    g = g.sort_values("pct", ascending=True)
    labels = [("Ward %g" % w) for w in g["ward"]]
    bars = ax.barh(labels, g["pct"])
    for b, p, n in zip(bars, g["pct"], g["n"]):
        ax.text(b.get_width() + 1, b.get_y() + b.get_height() / 2,
                "%.0f%%  (of %d households)" % (p, n), va="center", fontsize=9)
    ax.set_xlim(0, max(100, g["pct"].max() * 1.35))
    ax.set_xlabel("Households with more than 1 acre (% of households in the ward)")
    ax.set_ylabel("Ward")
    ax.set_title(TITLE, loc="left")
    fig.tight_layout()
    return fig
