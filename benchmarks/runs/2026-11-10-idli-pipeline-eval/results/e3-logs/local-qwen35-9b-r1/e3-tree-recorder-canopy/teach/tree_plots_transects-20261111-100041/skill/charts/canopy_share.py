TITLE = "Share of trees with canopy, by transect (%)"
QUESTION = "what share of trees have canopy"

def make(tables, plt):
    df = tables["Raw 10x10m Data"]
    df = df[df["canopy_y_n"].isin(["Y", "N"]) & df["transect"].notna()]
    fig, ax = plt.subplots(figsize=(9, 5))
    if len(df) == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    g = df.groupby("transect")["canopy_y_n"].agg(
        share=lambda s: 100.0 * (s == "Y").mean(), n="size")
    g = g.sort_values("share", ascending=True)
    overall = 100.0 * (df["canopy_y_n"] == "Y").mean()
    top = 15
    if len(g) > top:
        g = g.tail(top)
        note = f" (top {top} transects shown)"
    else:
        note = ""
    bars = ax.barh(g.index.astype(str), g["share"])
    ax.axvline(overall, color="grey", linestyle="--", linewidth=1)
    ax.text(overall, 1.01, f"All trees: {overall:.0f}%", transform=ax.get_xaxis_transform(),
            ha="center", va="bottom", fontsize=9, color="dimgrey")
    if len(g) <= 20:
        for b, (s, n) in zip(bars, zip(g["share"], g["n"])):
            ax.text(b.get_width() + 1, b.get_y() + b.get_height() / 2,
                    f"{s:.0f}% (n={int(n)})", va="center", fontsize=9)
    ax.set_xlim(0, 115)
    ax.set_xlabel("Trees with canopy (% of trees with a Y/N recorded)" + note)
    ax.set_ylabel("Transect")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig
