TITLE = "Share of households in debt, by village (%)"
QUESTION = "what share of households in each village are in debt"


def make(tables, plt):
    df = tables["Households"]
    fig, ax = plt.subplots(figsize=(9, 5))
    d = df[["village", "debts_inr"]].dropna()
    d = d[d["village"].astype(str).str.strip() != ""]
    if len(d) == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    d = d.assign(indebt=d["debts_inr"] > 0)
    g = d.groupby("village")["indebt"].agg(["sum", "count"])
    g["pct"] = 100 * g["sum"] / g["count"]
    g = g.sort_values("pct", ascending=True)
    ax.barh(g.index.astype(str), g["pct"])
    for i, (p, n, N) in enumerate(zip(g["pct"], g["sum"], g["count"])):
        ax.text(p + 1, i, f"{p:.0f}%  ({int(n)} of {int(N)})", va="center")
    ax.set_xlim(0, 115)
    ax.set_xlabel("Households with debts above 0 (% of households with a debt figure)")
    ax.set_ylabel("Village")
    ax.set_title(TITLE)
    fig.tight_layout()
    return fig
