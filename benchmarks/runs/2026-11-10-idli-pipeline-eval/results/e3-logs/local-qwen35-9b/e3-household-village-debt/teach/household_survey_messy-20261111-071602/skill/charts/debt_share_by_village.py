TITLE = "Share of households in debt, by village (%)"
QUESTION = "what share of households in each village are in debt"

def make(tables, plt):
    df = tables["Households"]
    fig, ax = plt.subplots(figsize=(9, 5))
    d = df[["village", "debts_inr"]].dropna()
    if len(d) == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    g = d.assign(indebt=d["debts_inr"] > 0).groupby("village")["indebt"].agg(["sum", "count"])
    g["pct"] = 100.0 * g["sum"] / g["count"]
    g = g.sort_values("pct")
    if len(g) > 15:
        g = g.tail(15)
    bars = ax.barh(g.index.astype(str), g["pct"])
    for b, (_, r) in zip(bars, g.iterrows()):
        ax.text(b.get_width() + 1, b.get_y() + b.get_height() / 2,
                f"{r['pct']:.0f}%  ({int(r['sum'])} of {int(r['count'])})", va="center")
    ax.set_xlim(0, 125)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("Households in debt (% of households with a readable debt figure)")
    ax.set_ylabel("Village")
    ax.set_title(TITLE)
    return fig
