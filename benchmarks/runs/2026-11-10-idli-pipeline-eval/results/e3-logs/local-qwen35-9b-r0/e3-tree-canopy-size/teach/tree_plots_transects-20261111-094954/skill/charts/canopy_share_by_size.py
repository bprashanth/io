TITLE = "Share of trees with canopy, by size class (%)"
QUESTION = "what share of trees in each size class have canopy"

def make(tables, plt):
    import pandas as pd
    df = tables["Raw 10x10m Data"]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    d = df[["dbh_1_cm", "canopy_y_n"]].copy()
    d["dbh_1_cm"] = pd.to_numeric(d["dbh_1_cm"], errors="coerce")
    d = d[d["dbh_1_cm"].notna() & d["canopy_y_n"].isin(["Y", "N"])]
    if d.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    def cls(x):
        return "Small" if x < 10 else ("Medium" if x <= 30 else "Large")
    d["size"] = d["dbh_1_cm"].map(cls)
    order = ["Small", "Medium", "Large"]
    rows = []
    for s in order:
        g = d[d["size"] == s]
        if len(g):
            rows.append((s, 100.0 * (g["canopy_y_n"] == "Y").mean(), len(g)))
    labels = {"Small": "Small (<10 cm)", "Medium": "Medium (10–30 cm)", "Large": "Large (>30 cm)"}
    names = [labels[r[0]] for r in rows]
    vals = [r[1] for r in rows]
    ys = list(range(len(rows)))
    ax.barh(ys, vals)
    ax.set_yticks(ys)
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Trees with canopy (% of trees in size class)")
    for y, r in zip(ys, rows):
        ax.text(r[1] + 1, y, f"{r[1]:.0f}%  (n = {r[2]})", va="center")
    ax.set_title(TITLE, loc="left")
    fig.tight_layout()
    return fig
