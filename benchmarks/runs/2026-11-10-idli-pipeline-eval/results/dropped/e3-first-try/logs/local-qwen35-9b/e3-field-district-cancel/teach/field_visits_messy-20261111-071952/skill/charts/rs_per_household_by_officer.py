TITLE = "Rs disbursed per household visited, by officer (cancelled left out)"
QUESTION = "which officers disburse far more or less per household"
def make(tables, plt):
    import pandas as pd
    df = tables["Visits"].copy()
    st = df["status_done_follow_up_cancelled"].astype(str).str.strip().str.lower()
    df = df[st != "cancelled"]
    df["amt"] = pd.to_numeric(df["amount_disbursed_rs"], errors="coerce")
    df["hh"] = pd.to_numeric(df["households_visited"], errors="coerce")
    df = df.dropna(subset=["field_officer", "amt", "hh"])
    fig, ax = plt.subplots(figsize=(9, 5))
    g = df.groupby("field_officer")[["amt", "hh"]].sum()
    g = g[g["hh"] > 0]
    if g.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center"); ax.axis("off"); return fig
    s = (g["amt"] / g["hh"]).sort_values()
    if len(s) > 20:
        s = s.iloc[-20:]
    bars = ax.barh(s.index.astype(str), s.values)
    if len(s) <= 15:
        ax.bar_label(bars, labels=[f"{v:,.0f}" for v in s.values], padding=3)
    overall = g["amt"].sum() / g["hh"].sum()
    ax.axvline(overall, linestyle="--", color="gray", linewidth=1)
    ax.text(overall, 1.01, f"all officers: {overall:,.0f}", transform=ax.get_xaxis_transform(), ha="center", fontsize=8)
    ax.set_xlabel("Rs per household visited"); ax.set_ylabel("Field officer")
    ax.margins(x=0.12); fig.tight_layout()
    return fig
