TITLE = "Share of trees with canopy, by transect (%)"
QUESTION = "what share of trees have canopy"


def make(tables, plt):
    df = tables["Raw 10x10m Data"]
    fig, ax = plt.subplots(figsize=(9, 5))
    d = df[df["canopy_y_n"].isin(["Y", "N"])]
    if d.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    overall = 100.0 * (d["canopy_y_n"] == "Y").mean()
    g = d.groupby("transect")["canopy_y_n"].agg(
        share=lambda s: 100.0 * (s == "Y").mean(), n="count")
    g = g.sort_values("share", ascending=True)
    top = 15
    if len(g) > top:
        g = g.tail(top)
    ax.barh(g.index.astype(str), g["share"])
    for i, (sh, n) in enumerate(zip(g["share"], g["n"])):
        ax.text(sh + 1, i, f"{sh:.0f}%  (of {int(n)} trees)", va="center", fontsize=8)
    ax.axvline(overall, color="grey", linestyle="--", linewidth=1)
    ax.text(overall, len(g) - 0.4, f" All trees: {overall:.0f}%", color="grey",
            va="bottom", fontsize=9)
    ax.set_xlim(0, 115)
    ax.set_xlabel("Trees with canopy (% of trees with canopy recorded Y or N)")
    ax.set_ylabel("Transect")
    ax.set_title(TITLE)
    return fig
