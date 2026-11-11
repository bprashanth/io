TITLE = "Share of households in debt, by village (%)"
QUESTION = "what share of households in each village are in debt?"


def make(tables, plt):
    df = tables["Households"].copy()
    fig, ax = plt.subplots(figsize=(9, 5))
    df = df[df["household_id"].isna() | ~df["household_id"].duplicated()]
    total = len(df)
    df = df[df["village"].notna() & df["debts_inr"].notna()]
    skipped = total - len(df)
    if df.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    g = df.groupby("village")["debts_inr"].agg(
        n="count", debt=lambda s: int((s > 0).sum()))
    g["share"] = 100.0 * g["debt"] / g["n"]
    g = g.sort_values("share", ascending=False)
    if len(g) > 15:
        g = g.head(15)
    g = g.iloc[::-1]
    bars = ax.barh(g.index.astype(str), g["share"])
    for b, (_, r) in zip(bars, g.iterrows()):
        ax.text(b.get_width() + 1, b.get_y() + b.get_height() / 2,
                f"{r['share']:.0f}%  ({int(r['debt'])} of {int(r['n'])})",
                va="center", fontsize=9)
    ax.set_xlim(0, 118)
    ax.set_xlabel("Households with debts above 0 (% of households in the village)")
    ax.set_ylabel("Village")
    ax.set_title(TITLE)
    if skipped:
        fig.text(0.01, 0.01, f"Left out: {skipped} households with a blank/unreadable debt or village, or a repeated ID.",
                 fontsize=8)
    return fig
