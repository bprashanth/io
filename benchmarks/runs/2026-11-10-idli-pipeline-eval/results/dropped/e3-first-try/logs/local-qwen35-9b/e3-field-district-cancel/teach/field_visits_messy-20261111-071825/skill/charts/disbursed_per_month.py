TITLE = "Amount disbursed per month (Rs, cancelled visits left out)"
QUESTION = "is field disbursement rising, falling or seasonal"
def make(tables, plt):
    import pandas as pd
    df = tables["Visits"].copy()
    st = df["status_done_follow_up_cancelled"].astype(str).str.strip().str.lower()
    df = df[st != "cancelled"]
    df["d"] = pd.to_datetime(df["visit_date"], errors="coerce")
    df["amt"] = pd.to_numeric(df["amount_disbursed_rs"], errors="coerce")
    df = df.dropna(subset=["d", "amt"])
    fig, ax = plt.subplots(figsize=(9, 5))
    if df.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center"); ax.axis("off"); return fig
    m = df.groupby(df["d"].dt.to_period("M"))["amt"].sum()
    m = m.reindex(pd.period_range(m.index.min(), m.index.max(), freq="M"), fill_value=0)
    ax.plot(m.index.to_timestamp(), m.values, marker="o")
    ax.set_xlabel("Month"); ax.set_ylabel("Amount disbursed (Rs)")
    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f"{v:,.0f}"))
    fig.autofmt_xdate(); fig.tight_layout()
    return fig
