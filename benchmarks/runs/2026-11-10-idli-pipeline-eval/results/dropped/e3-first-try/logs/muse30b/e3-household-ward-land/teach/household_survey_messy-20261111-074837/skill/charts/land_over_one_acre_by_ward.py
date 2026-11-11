TITLE = "Share of households with more than one acre of land, by ward (%)"
QUESTION = "what share of households have more than one acre, by ward"


def make(tables, plt):
    df = tables["Households"].copy()
    fig, ax = plt.subplots(figsize=(9, 5))
    df = df[df["ward"].notna() & df["land_acres"].notna()]
    if df["household_id"].notna().any():
        df = df[df["household_id"].isna() | ~df["household_id"].duplicated()]
    if df.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    df["big"] = df["land_acres"] > 1
    g = df.groupby("ward")["big"].agg(["mean", "sum", "count"])
    g["pct"] = g["mean"] * 100
    g = g.sort_values("pct")
    labels = [str(int(w)) if float(w).is_integer() else str(w) for w in g.index]
    labels = ["Ward " + l for l in labels]
    bars = ax.barh(labels, g["pct"])
    show = len(g) <= 15
    if show:
        for b, (_, r) in zip(bars, g.iterrows()):
            ax.text(b.get_width() + 0.5, b.get_y() + b.get_height() / 2,
                    f"{r['pct']:.0f}%  ({int(r['sum'])} of {int(r['count'])})",
                    va="center", fontsize=9)
    ax.set_xlim(0, max(100, g["pct"].max() * 1.25) if g["pct"].max() > 80 else g["pct"].max() * 1.35 + 1)
    ax.set_xlabel("Households with more than 1 acre (% of households in the ward)")
    ax.set_title(TITLE, loc="left")
    return fig
