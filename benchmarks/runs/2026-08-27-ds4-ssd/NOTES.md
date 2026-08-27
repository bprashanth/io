# DS4 / DeepSeek-V4-Flash SSD-streaming experiment (staging: DGX GB10)

Machine: GB10 (aarch64), 121 GiB unified, shared with live vLLM (42 GiB GPU) and two
llama-servers (~16 GiB) - NOT a quiet box; treat all throughput as a floor.
Model: DeepSeek-V4-Flash 670B MoE, IQ2XXS imatrix GGUF, 81 GiB (the Q2-imatrix
low-memory build). Engine: ds4 (prebuilt in ../idlisseus/ds4). Server: ds4-server,
OpenAI-compatible, tool calls supported.

## Findings so far

1. **cgroup MemoryMax breaks CUDA context init on unified memory** ("CUDA set device
   failed: out of memory" inside a 26G scope that never OOM-killed). The Mac-budget
   simulation must come from ds4's own bounds (--ssd-streaming-cache-experts) plus
   external RSS monitoring, not cgroups. ds4 sets oom_score_adj=1000 on itself - it
   dies first under real pressure, machine-safe.
2. **--ssd-streaming is Metal/CUDA/ROCm only**; --cpu cannot stream.
3. Internal NVMe (2.9 GB/s) baseline, cache 10GB, ctx 8192:
   startup ~15 s; 200 tokens in ~139 s = **1.44 tok/s**; cold == warm exactly; server
   RSS just 1.1 GiB (experts ride the OS page cache, not process RSS). Cold==warm on
   fast disk means decode here is compute-bound (GPU shared with vLLM/llama), not
   IO-bound - this box measures the floor, not the Mac ceiling (M4 Max reports: 3.2).
4. Seagate (USB spinning disk, ~130 MB/s, exFAT): server startup **12 s** - lazy mmap
   makes "loading" instant; the disk is billed per expert fault instead.

## Pending
seagate cold/warm battery; dashboard-length request; planner eval (3 mock tools);
memory peak tracking; fallback decision (Qwen3.8-27B 4-bit on same SSD).
