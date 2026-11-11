TITLE = "Share of visits by status (% of all visits)"
QUESTION = "what share of visits were Done / Follow-up / Cancelled overall"

def make(tables, plt):
    df = tables["Visits"]
    col = "status_done_follow_up_cancelled"
    fig, ax = plt.subplots(figsize=(9, 5))
    s = df[col].astype("string").str.strip() if col in df else None
    if s is None:
        ax.text(0.5, 0.5, "No data", ha="center", va="center"); ax.axis("off"); return fig
    s = s.fillna("(blank)").replace("", "(blank)")
    counts = s.value_counts()
    if len(counts) > 8:
        rest = int(counts.iloc[7:].sum())
        counts = counts.iloc[:7].copy()
        counts["Others"] = rest
    total = int(s.shape[0])
    if total == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center"); ax.axis("off"); return fig
    share = (counts / total * 100)
    share = share.sort_values()
    ax.barh(share.index.astype(str), share.values)
    for i, (v, n) in enumerate(zip(share.values, counts[share.index].values)):
        ax.text(v + share.max() * 0.01, i, f"{v:.1f}%  ({int(n)})", va="center")
    ax.set_xlim(0, share.max() * 1.2)
    ax.set_xlabel(f"Share of all {total} visits (%)")
    ax.set_title(TITLE)
    return fig
