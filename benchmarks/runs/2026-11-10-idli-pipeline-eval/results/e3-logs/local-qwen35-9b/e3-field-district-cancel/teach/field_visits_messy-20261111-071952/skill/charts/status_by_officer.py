TITLE = "Visits by status, per officer (number of visits)"
QUESTION = "who has the most follow-ups or cancellations"
def make(tables, plt):
    import pandas as pd
    df = tables["Visits"].copy()
    df = df.dropna(subset=["field_officer", "status_done_follow_up_cancelled"])
    fig, ax = plt.subplots(figsize=(9, 5))
    if df.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center"); ax.axis("off"); return fig
    c = df.groupby(["field_officer", "status_done_follow_up_cancelled"]).size().unstack(fill_value=0)
    c = c.loc[c.sum(axis=1).sort_values().index]
    if len(c) > 20:
        c = c.iloc[-20:]
    left = None
    for col in c.columns:
        ax.barh(c.index.astype(str), c[col].values, left=left, label=str(col))
        left = c[col].values if left is None else left + c[col].values
    ax.legend(title="Status", frameon=False, fontsize=8)
    ax.set_xlabel("Number of visits"); ax.set_ylabel("Field officer")
    fig.tight_layout()
    return fig
