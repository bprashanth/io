TITLE = "Share of trees with canopy, by size class (% of trees)"
QUESTION = "what share of trees in each size class have canopy"

def make(tables, plt):
    import pandas as pd
    df = tables["Raw 10x10m Data"].copy()
    d = pd.to_numeric(df["dbh_1_cm"], errors="coerce")
    df["size"] = pd.cut(d, [-float("inf"), 10, 30, float("inf")], labels=["Small", "Medium", "Large"], right=False)
    # size rules: Small < 10, Medium 10-30 inclusive, Large > 30
    df.loc[d == 30, "size"] = "Medium"
    df = df[df["size"].notna() & df["canopy_y_n"].isin(["Y", "N"])]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    if df.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    order = ["Small", "Medium", "Large"]
    g = df.groupby("size", observed=False)["canopy_y_n"]
    n = g.size().reindex(order).fillna(0)
    y = g.apply(lambda s: (s == "Y").sum()).reindex(order).fillna(0)
    share = (100 * y / n.where(n > 0)).fillna(0)
    labels = ["%s DBH 1\n(%d trees)" % (c, n[c]) for c in order]
    bars = ax.barh(labels, share.values)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Trees with canopy (% of trees in the size class)")
    for b, s, yy, nn in zip(bars, share.values, y.values, n.values):
        txt = "%.0f%%  (%d of %d)" % (s, yy, nn) if nn else "no trees"
        ax.text(min(s + 1.5, 70), b.get_y() + b.get_height() / 2, txt, va="center")
    ax.set_title(TITLE, loc="left")
    fig.text(0.01, 0.01, "Small: under 10 cm; Medium: 10 to 30 cm; Large: over 30 cm. Trees without a size or a Y/N canopy are left out.", fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    return fig
