# Agent notes

Read `README.md`, then the local `checkpoint/CHECKPOINT.md` if it exists. Treat
the current local-first ladder as the baseline until its frozen evidence fails
reproduction; do not silently redesign it or overfit to benchmark sectors.

Raw runs are evidence. Never rewrite them to improve a result. Record new work
under `benchmarks/runs/`, derive aggregates under `benchmarks/results/`, and
append a timestamped `chronology/` entry. Keep private data local/DGX; the
OpenRouter key is at `~/.config/idlisseus/openrouter.json` and must never be
printed, copied into a workspace, or committed.

Use Cursor `agent -p` or `claude -p` with a cheaper model for bounded mechanical
work when useful. Give it a narrow task, prefer read-only mode or a disposable
worktree, and review its output yourself. Keep architecture, privacy decisions,
benchmark validity and final grading with the primary agent.
