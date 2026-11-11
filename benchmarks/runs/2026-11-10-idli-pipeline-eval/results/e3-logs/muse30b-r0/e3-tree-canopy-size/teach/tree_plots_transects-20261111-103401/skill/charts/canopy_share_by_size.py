TITLE = "Share of trees with canopy, by size class (%)"
QUESTION = "what share of trees in each size class have canopy"

def make(tables, plt):
    import pandas as pd
    df = tables["Raw 10x10m Data"].copy()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    dbh = pd.to_numeric(df["dbh_1_cm"], errors="coerce")
    df["size"] = pd.cut(dbh, [-float("inf"), 10, 30, float("inf")], right=False,
                        labels=["Small (<10 cm)", "Medium (10-30 cm)", "Large (>30 cm)"])
    # dbh exactly 30 belongs to Medium (matches the skill: < 10 small, <= 30 medium)
    df.loc[dbh == 30, "size"] = "Medium (10-30 cm)"
    df = df[df["size"].notna() & df["canopy_y_n"].isin(["Y", "N"])]
    if df.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    g = df.groupby("size", observed=False)["canopy_y_n"].agg(
        n="count", y=lambda s: (s == "Y").sum())
    g = g[g["n"] > 0]
    g["pct"] = 100.0 * g["y"] / g["n"]
    labels = [f"{i}\n(n={int(r.n)})" for i, r in g.iterrows()]
    bars = ax.barh(labels, g["pct"])
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Trees with canopy (% of trees measured in the size class)")
    for b, (_, r) in zip(bars, g.iterrows()):
        ax.text(b.get_width() + 1, b.get_y() + b.get_height() / 2,
                f"{r.pct:.0f}%  ({int(r.y)} of {int(r.n)})", va="center")
    ax.set_title(TITLE, loc="left")
    fig.tight_layout()
    return fig
