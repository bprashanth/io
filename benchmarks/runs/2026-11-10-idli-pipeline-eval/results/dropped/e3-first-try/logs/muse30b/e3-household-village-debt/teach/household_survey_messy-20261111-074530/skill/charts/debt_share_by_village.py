TITLE = "Share of households in debt, by village (%)"
QUESTION = "what share of households in each village are in debt"

def make(tables, plt):
    df = tables["Households"]
    fig, ax = plt.subplots(figsize=(9, 5))
    d = df[["village", "debts_inr"]].copy()
    d["debts_inr"] = d["debts_inr"].astype(float)
    d = d.dropna(subset=["village", "debts_inr"])
    if d.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    d["in_debt"] = d["debts_inr"] > 0
    g = d.groupby("village")["in_debt"].agg(["mean", "sum", "count"])
    g["pct"] = g["mean"] * 100
    g = g.sort_values("pct")
    bars = ax.barh(g.index.astype(str), g["pct"])
    for b, (_, r) in zip(bars, g.iterrows()):
        ax.text(b.get_width() + 1, b.get_y() + b.get_height() / 2,
                f"{r['pct']:.0f}%  ({int(r['sum'])} of {int(r['count'])})",
                va="center", fontsize=9)
    ax.set_xlim(0, 118)
    ax.set_xlabel("Households with debt above 0 (% of households with a readable debt)")
    ax.set_ylabel("Village")
    ax.set_title(TITLE)
    return fig
