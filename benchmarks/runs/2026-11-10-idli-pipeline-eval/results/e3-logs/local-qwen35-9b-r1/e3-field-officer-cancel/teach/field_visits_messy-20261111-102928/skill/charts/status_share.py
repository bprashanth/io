TITLE = "Share of visits by status (% of all visits)"
QUESTION = "what share of visits were in each status, overall"

def make(tables, plt):
    df = tables["Visits"]
    col = "status_done_follow_up_cancelled"
    fig, ax = plt.subplots(figsize=(9, 5))
    if df is None or len(df) == 0 or col not in df.columns:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    s = df[col].astype("string").str.strip()
    s = s.where(s.notna() & (s != ""), "(blank)")
    key = s.str.lower()
    label = s.groupby(key).agg(lambda x: x.value_counts().index[0])
    counts = key.value_counts()
    total = int(counts.sum())
    top = 8
    names = [label[k] for k in counts.index]
    vals = list(counts.values)
    if len(vals) > top:
        other = sum(vals[top:])
        names, vals = names[:top], vals[:top]
        names.append("Others"); vals.append(other)
    pct = [v * 100.0 / total for v in vals]
    order = list(range(len(vals)))[::-1]
    ax.barh([names[i] for i in order], [pct[i] for i in order])
    for y, i in enumerate(order):
        ax.text(pct[i], y, f"  {pct[i]:.1f}% ({vals[i]})", va="center")
    ax.set_xlabel(f"Share of visits (%), out of {total} visits")
    ax.set_xlim(0, max(pct) * 1.25)
    ax.set_title(TITLE, loc="left")
    fig.tight_layout()
    return fig
