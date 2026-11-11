TITLE = "Share of households with more than 1 acre of land, by ward (%)"
QUESTION = "share of households with more than one acre of land, by ward"


def make(tables, plt):
    df = tables["Households"].copy()
    fig, ax = plt.subplots(figsize=(9, 5))
    df = df[df["ward"].notna() & df["land_acres"].notna()]
    if "household_id" in df.columns:
        df = df.drop_duplicates(subset="household_id")
    if df.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    df["big"] = df["land_acres"] > 1
    g = df.groupby("ward")["big"].agg(["sum", "count"])
    g["pct"] = 100.0 * g["sum"] / g["count"]
    g = g.sort_values("pct")
    labels = [("Ward %g" % w) for w in g.index]
    bars = ax.barh(labels, g["pct"])
    for b, (_, r) in zip(bars, g.iterrows()):
        ax.text(b.get_width() + 0.5, b.get_y() + b.get_height() / 2,
                "%.0f%%  (%d of %d)" % (r["pct"], r["sum"], r["count"]),
                va="center", fontsize=9)
    ax.set_xlim(0, max(100, g["pct"].max() * 1.25) if g["pct"].max() > 80 else g["pct"].max() * 1.35 + 1)
    ax.set_xlabel("Households with more than 1 acre (% of households with land recorded)")
    ax.set_title(TITLE, loc="left")
    fig.tight_layout()
    return fig
