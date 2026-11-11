TITLE = "Amount disbursed by officer's district (Rs, cancelled visits left out)"
QUESTION = "disbursement by officer district"

def make(tables, plt):
    df = tables["Visits"].copy()
    fig, ax = plt.subplots(figsize=(9, 5))
    status = "status_done_follow_up_cancelled"
    if status in df.columns:
        df = df[df[status].astype(str).str.strip().str.lower() != "cancelled"]
    df = df[df["officer_district"].notna() & df["amount_disbursed_rs"].notna()]
    if df.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig
    s = df.groupby("officer_district")["amount_disbursed_rs"].sum().sort_values()
    if len(s) > 12:
        top = s.iloc[-11:]
        s = (s.iloc[:-11].sum() and None) or top
        import pandas as pd
        others = df.groupby("officer_district")["amount_disbursed_rs"].sum().sort_values().iloc[:-11].sum()
        s = pd.concat([pd.Series({"Others": others}), top])
    bars = ax.barh(s.index.astype(str), s.values)
    show = len(s) <= 15
    if show:
        for b, v in zip(bars, s.values):
            ax.text(v, b.get_y() + b.get_height() / 2, f" Rs {v:,.0f}", va="center", fontsize=9)
        ax.set_xlim(0, s.max() * 1.18)
    ax.set_xlabel("Amount disbursed (Rs)")
    ax.set_ylabel("Officer's district")
    ax.set_title(TITLE)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x:,.0f}"))
    fig.tight_layout()
    return fig
