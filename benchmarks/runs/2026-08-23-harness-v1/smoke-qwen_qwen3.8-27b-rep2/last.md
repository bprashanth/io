

I can't complete the run step — every shell command in this environment is failing at sandbox startup:

```
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
```

I retried several times with different shells, TTY modes, and working directories; the failure is in the `bwrap` sandbox initialization itself (it can't configure the loopback interface), so I have no way to read the CSV, create the script file, or run Python. Escalated execution is also disabled by the current approval policy.

Here's the script you can run as-is:

```python
import pandas as pd

df = pd.read_csv("handpump_survey.csv")

block_col = next(c for c in df.columns if "block" in c.lower())
status_col = next(c for c in df.columns
                  if any(k in c.lower() for k in ("functional", "status", "condition")))

is_nonfunctional = df[status_col].astype(str).str.lower().str.contains(r"not|non", regex=True)

table = (
    df.loc[is_nonfunctional]
    .groupby(block_col)
    .size()
    .rename("non_functional_count")
    .sort_values(ascending=False)
    .reset_index()
)

print(table.to_string(index=False))
```

Run it with:

```
/home/beeps/src/github.com/bprashanth/io/.venv-v2/bin/python handpump_nonfunctional_by_block.py
```

Notes:
- The script auto-detects the block and functional-status columns (matching `block`, and `functional`/`status`/`condition` in the header) and counts rows whose status contains "not"/"non", then prints a sorted table per block.
- If your CSV uses different wording (e.g., "working status: No" or "defective"), tell me the actual header row and I'll adjust the filter.

If you can restart this session with the sandbox fixed — or paste the CSV header plus a few rows — I'll finalize the script and produce the actual per-block table.