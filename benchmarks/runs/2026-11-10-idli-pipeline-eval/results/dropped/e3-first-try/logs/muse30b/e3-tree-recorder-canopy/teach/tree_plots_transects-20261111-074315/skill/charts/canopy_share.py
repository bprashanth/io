TITLE = "Share of trees with canopy, by transect (%)"
QUESTION = "what share of trees have canopy"


def make(tables, plt):
    df = tables["Raw 10x10m Data"]
    fig, ax = plt.subplots(figsize=(9, 5))
    c = df["canopy_y_n"].astype("string").str.strip().str.upper()
    known = df[c.isin(["Y", "N"])].copy()
    known["has"] = c[c.isin(["Y", "N"])] == "Y"
    if len(known) == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    g = known.groupby("transect")["has"].agg(["sum", "count"])
    g["pct"] = 100 * g["sum"] / g["count"]
    g = g.sort_values("pct")
    if len(g) > 12:
        g = g.tail(12)
    overall = 100 * known["has"].mean()
    bars = ax.barh(g.index.astype(str), g["pct"])
    for b, (_, r) in zip(bars, g.iterrows()):
        ax.text(b.get_width() + 1, b.get_y() + b.get_height() / 2,
                f"{r['pct']:.0f}% ({int(r['sum'])} of {int(r['count'])})", va="center", fontsize=9)
    ax.axvline(overall, linestyle="--", color="gray", linewidth=1)
    ax.text(overall, len(g) - 0.4, f" All trees: {overall:.0f}%", color="gray", fontsize=9, va="bottom")
    ax.set_xlim(0, 115)
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.set_xlabel("Trees with canopy (% of trees with a Y/N answer)")
    ax.set_title(TITLE, loc="left")
    fig.tight_layout()
    return fig
