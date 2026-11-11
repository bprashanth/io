TITLE = "Amount disbursed by village (Rs, cancelled visits left out)"
QUESTION = "which villages get the most money"
def make(tables, plt):
    import pandas as pd
    df = tables["Visits"].copy()
    st = df["status_done_follow_up_cancelled"].astype(str).str.strip().str.lower()
    df = df[st != "cancelled"]
    df["amt"] = pd.to_numeric(df["amount_disbursed_rs"], errors="coerce")
    df = df.dropna(subset=["village", "amt"])
    fig, ax = plt.subplots(figsize=(9, 5))
    if df.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center"); ax.axis("off"); return fig
    s = df.groupby("village")["amt"].sum().sort_values(ascending=False)
    if len(s) > 12:
        s = pd.concat([s.iloc[:11], pd.Series({"Others": s.iloc[11:].sum()})])
    s = s.iloc[::-1]
    bars = ax.barh(s.index.astype(str), s.values)
    if len(s) <= 15:
        ax.bar_label(bars, labels=[f"{v:,.0f}" for v in s.values], padding=3)
    ax.set_xlabel("Amount disbursed (Rs)"); ax.set_ylabel("Village")
    ax.margins(x=0.12); fig.tight_layout()
    return fig
