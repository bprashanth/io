# Kernel / shell split is a module boundary, not a process boundary

**Now.** `app/io-desktop/server/io_service.py` holds the kernel (loader, DuckDB execution, renderer,
skills, SEE WHY, interaction log) *and* two shells (HTTP/desktop UI routes, Telegram bot thread) in one
file. The harness skill (`benchmarks/t0/harness-skill/io.py`) imports the same module, so there is
one kernel, but the split is by function, not by package.

**Why ignored.** No regression risk before the event; every shell already talks only to `WS`,
`execute`, `run_ask/run_build/run_page`, `load_config`. Splitting files is mechanical.

**Later.** `iokernel/` (loader.py, skills.py, execute.py, render_plan.py, manifest.py, vault/guard
when sheltering lands) with `io.py` as its CLI contract; `shells/desktop`, `shells/telegram`,
`shells/agent` (Hermes toolset). The Antigravity shield's interceptor becomes `iokernel/egress.py`
and every shell's model traffic goes through it (one chokepoint, one egress log).
