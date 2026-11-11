TITLE = "Share of trees with canopy, by transect (%)"
QUESTION = "what share of trees have canopy"


def make(tables, plt):
    df = tables["Raw 10x10m Data"]
    fig, ax = plt.subplots(figsize=(9, 5))
    d = df[df["canopy_y_n"].isin(["Y", "N"])]
    if len(d) == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    g = d.groupby("transect")["canopy_y_n"].agg(total="count", canopy=lambda s: (s == "Y").sum())
    g["share"] = 100.0 * g["canopy"] / g["total"]
    g = g.sort_values("share", ascending=False)
    if len(g) > 15:
        top = g.head(15)
        rest = g.iloc[15:]
        others = rest[["total", "canopy"]].sum()
        top.loc["Others"] = [others["total"], others["canopy"], 100.0 * others["canopy"] / others["total"]]
        g = top
    g = g.iloc[::-1]
    bars = ax.barh(g.index.astype(str), g["share"])
    if len(g) <= 20:
        for b, (_, r) in zip(bars, g.iterrows()):
            ax.text(b.get_width() + 1, b.get_y() + b.get_height() / 2,
                    f"{r['share']:.0f}%  ({int(r['canopy'])} of {int(r['total'])})",
                    va="center", fontsize=8)
    overall = 100.0 * (d["canopy_y_n"] == "Y").sum() / len(d)
    ax.set_xlim(0, 115)
    ax.set_xlabel("Trees with canopy (% of trees with canopy recorded)")
    ax.set_ylabel("Transect")
    ax.set_title(f"Share of trees with canopy, by transect (overall {overall:.0f}%)")
    return fig
