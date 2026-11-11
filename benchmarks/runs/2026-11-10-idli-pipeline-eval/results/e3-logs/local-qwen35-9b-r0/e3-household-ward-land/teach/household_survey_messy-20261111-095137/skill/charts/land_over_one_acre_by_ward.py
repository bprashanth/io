TITLE = "Share of households with more than 1 acre of land, by ward (%)"
QUESTION = "what share of households have more than one acre, by ward"


def make(tables, plt):
    df = tables["Households"]
    fig, ax = plt.subplots(figsize=(9, 5))
    df = df[df["land_acres"].notna() & df["ward"].notna()]
    if len(df) == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    g = df.groupby("ward").agg(total=("land_acres", "size"),
                               over=("land_acres", lambda s: int((s > 1).sum())))
    g["pct"] = 100.0 * g["over"] / g["total"]
    g = g.sort_values("pct", ascending=True)
    labels = [str(int(w)) if float(w).is_integer() else str(w) for w in g.index]
    labels = ["Ward " + l for l in labels]
    bars = ax.barh(labels, g["pct"])
    few = len(g) <= 15
    if few:
        for b, (_, r) in zip(bars, g.iterrows()):
            ax.text(b.get_width() + 0.8, b.get_y() + b.get_height() / 2,
                    f"{r['pct']:.0f}%  ({int(r['over'])} of {int(r['total'])})",
                    va="center", fontsize=9)
    ax.set_xlim(0, max(100, g["pct"].max() * 1.25) if g["pct"].max() > 80 else max(g["pct"].max() * 1.4, 10))
    ax.set_xlabel("% of households with more than 1 acre (households with land recorded)")
    ax.set_title(TITLE, loc="left")
    fig.tight_layout()
    return fig
