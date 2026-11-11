TITLE = "Share of trees with canopy, by transect (% of trees)"
QUESTION = "what share of trees have canopy"

def make(tables, plt):
    df = tables["Raw 10x10m Data"]
    fig, ax = plt.subplots(figsize=(9, 5))
    d = df[df["canopy_y_n"].isin(["Y", "N"])]
    if len(d) == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    g = d.groupby("transect")["canopy_y_n"].agg(
        trees="size", canopy=lambda s: (s == "Y").sum())
    g["share"] = 100.0 * g["canopy"] / g["trees"]
    g = g.sort_values("share", ascending=False)
    overall = 100.0 * (d["canopy_y_n"] == "Y").mean()
    top = g.head(15)
    others = g.iloc[15:]
    labels = list(top.index)
    vals = list(top["share"])
    counts = list(top["trees"])
    if len(others):
        labels.append("Others")
        vals.append(100.0 * others["canopy"].sum() / others["trees"].sum())
        counts.append(int(others["trees"].sum()))
    y = list(range(len(labels)))
    ax.barh(y, vals)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.axvline(overall, color="grey", linestyle="--", linewidth=1)
    ax.text(overall, -0.7, f" overall {overall:.0f}%", color="grey", va="bottom", fontsize=9)
    if len(labels) <= 15:
        for yi, v, n in zip(y, vals, counts):
            ax.text(v + 1, yi, f"{v:.0f}%  (n={n})", va="center", fontsize=9)
    ax.set_xlim(0, 110)
    ax.set_xlabel("Trees with canopy (% of trees with a Y/N entry)")
    ax.set_ylabel("Transect")
    ax.set_title(TITLE)
    return fig
