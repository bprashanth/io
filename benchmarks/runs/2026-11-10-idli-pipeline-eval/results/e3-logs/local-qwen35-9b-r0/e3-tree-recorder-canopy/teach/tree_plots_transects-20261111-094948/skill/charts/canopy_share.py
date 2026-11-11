import math

TITLE = "Share of trees with canopy, by transect and plot (% of tree records)"
QUESTION = "what share of trees have canopy"

def make(tables, plt):
    # Only the raw tree records (one row per tree): no seedlings, no Cestrum totals.
    df = tables["Raw 10x10m Data"]
    d = df[df["canopy_y_n"].isin(["Y", "N"]) & df["transect"].notna() & df["plot"].notna()].copy()
    if len(d) == 0:
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    # Native/Alien comes from the Species key; the team's own codes are not in the key.
    d["origin"] = d["sp_native_alien"].fillna("").astype(str).str.strip()
    d.loc[d["origin"] == "", "origin"] = "Not in species key"
    d["has"] = (d["canopy_y_n"] == "Y").astype(float)
    order = d["origin"].value_counts().index.tolist()
    if "Not in species key" in order:
        order = [o for o in order if o != "Not in species key"] + ["Not in species key"]
    transects = sorted(d["transect"].unique(), key=str)
    shown = transects[:12]
    ncol = 2 if len(shown) > 1 else 1
    nrow = math.ceil(len(shown) / ncol)
    heights = [max(1, d[d["transect"] == t]["plot"].nunique()) for t in shown]
    fig, axes = plt.subplots(nrow, ncol, figsize=(10, max(4, 0.45 * sum(heights) / ncol * (len(order) + 1) * 0.6 + 1.5 * nrow)),
                             squeeze=False)
    flat = list(axes.ravel())
    k = len(order)
    bh = 0.8 / k
    for ax, t in zip(flat, shown):
        s = d[d["transect"] == t]
        plots = sorted(s["plot"].unique())
        for j, o in enumerate(order):
            so = s[s["origin"] == o].groupby("plot")["has"].agg(["mean", "size"])
            ys, vals, ns = [], [], []
            for i, p in enumerate(plots):
                if p in so.index:
                    ys.append(i - 0.4 + bh * (j + 0.5))
                    vals.append(100.0 * so.loc[p, "mean"])
                    ns.append(int(so.loc[p, "size"]))
            bars = ax.barh(ys, vals, height=bh * 0.92, label=o)
            if len(plots) * k <= 24:
                for b, v, n in zip(bars, vals, ns):
                    ax.text(b.get_width() + 1, b.get_y() + b.get_height() / 2, "%.0f%% (n=%d)" % (v, n),
                            va="center", fontsize=7)
        ax.set_yticks(range(len(plots)))
        ax.set_yticklabels([("%g" % p) for p in plots])
        ax.invert_yaxis()
        ax.set_xlim(0, 130)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.set_title(str(t), fontsize=11)
        ax.set_ylabel("Plot")
        ax.set_xlabel("Trees with canopy (% of tree records)")
    for ax in flat[len(shown):]:
        ax.set_axis_off()
    h, l = flat[0].get_legend_handles_labels()
    fig.legend(h, l, title="Species origin (Native / Alien, from the species key)", loc="upper left",
               bbox_to_anchor=(0.0, 0.95), ncol=len(l), fontsize=9, title_fontsize=9, alignment="left")
    fig.suptitle(TITLE, x=0.01, ha="left", fontsize=12, fontweight="bold")
    if len(transects) > len(shown):
        fig.text(0.01, 0.005, "Showing the first %d of %d transects." % (len(shown), len(transects)), fontsize=8)
    fig.tight_layout(rect=(0, 0.02, 1, 0.88))
    return fig
