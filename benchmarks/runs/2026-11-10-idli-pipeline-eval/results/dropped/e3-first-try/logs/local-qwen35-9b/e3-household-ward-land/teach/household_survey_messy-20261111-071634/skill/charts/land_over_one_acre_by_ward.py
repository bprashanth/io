TITLE = "Share of households with more than 1 acre of land, by ward (%)"
QUESTION = "what share of households have more than one acre, by ward"


def make(tables, plt):
    df = tables["Households"]
    fig, ax = plt.subplots(figsize=(9, 5))
    d = df[["ward", "land_acres"]].dropna()
    if d.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    d = d.assign(big=d["land_acres"] > 1)
    g = d.groupby("ward").agg(n=("big", "size"), share=("big", "mean"))
    g["share"] = g["share"] * 100
    g = g.sort_values("share", ascending=True)
    if len(g) > 15:
        g = g.tail(15)
    labels = [str(int(w)) if float(w).is_integer() else str(w) for w in g.index]
    bars = ax.barh(["Ward " + l for l in labels], g["share"])
    show = len(g) <= 20
    if show:
        for b, s, n in zip(bars, g["share"], g["n"]):
            ax.text(b.get_width() + 1, b.get_y() + b.get_height() / 2,
                    f"{s:.0f}%  ({n} households)", va="center", fontsize=9)
    ax.set_xlim(0, 100)
    ax.set_xlabel("% of households with more than 1 acre (households with a land figure)")
    ax.set_title(TITLE)
    return fig
