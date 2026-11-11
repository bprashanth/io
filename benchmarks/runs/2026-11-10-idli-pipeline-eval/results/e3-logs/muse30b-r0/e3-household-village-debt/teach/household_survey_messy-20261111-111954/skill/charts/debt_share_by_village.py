TITLE = "Share of households in debt, by village (%)"
QUESTION = "what share of households in each village are in debt"

def make(tables, plt):
    df = tables["Households"]
    fig, ax = plt.subplots(figsize=(9, 5))
    d = df[df["village"].notna() & df["debts_inr"].notna()]
    if len(d) == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    g = d.groupby("village")["debts_inr"].agg(total="count", indebted=lambda s: int((s > 0).sum()))
    g["share"] = 100.0 * g["indebted"] / g["total"]
    g = g.sort_values("share", ascending=False)
    if len(g) > 15:
        g = g.head(15)
    g = g.iloc[::-1]
    bars = ax.barh(g.index.astype(str), g["share"])
    for b, (_, r) in zip(bars, g.iterrows()):
        ax.text(b.get_width() + 1, b.get_y() + b.get_height() / 2,
                f"{r['share']:.0f}%  ({int(r['indebted'])} of {int(r['total'])})", va="center")
    ax.set_xlim(0, 118)
    ax.set_xlabel("Households in debt (% of households with a readable debt figure)")
    ax.set_title(TITLE)
    return fig
