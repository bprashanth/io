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

5. **Seagate streaming: DNF.** Three consecutive 200-token requests all timed out at
   30 minutes with zero tokens; the drive sat at 98% util / 93 MB/s the whole time and
   ds4 was still warming its expert cache. Experts are ~6.75 MiB random reads; a
   spinning USB drive collapses there. **Streaming an 81 GiB MoE needs NVMe-class
   (USB4/Thunderbolt) media - a spinning event drive is a hard no.**
6. **Fallback measured on the same drive - and it wins.** Qwen3.8-27B UD-Q4_K_M
   (17 GiB, unsloth GGUF) pulled onto the Seagate: llama.cpp loads it in **111 s**
   (dense loads are sequential - the one thing a spinning disk does fine), then runs
   from RAM at **4.05 tok/s CPU-only** (12 threads, contended box; a Mac's Metal path
   would be several times faster). Fits the 32 GB budget with room. Already 3x the
   ds4 floor here and above the proposal's 1.5-2 tok/s bar.

## Emerging recommendation

On this evidence: for THIS class of drive, the event kit's "big local brain" should be
**Qwen3.8-27B Q4 loaded whole from the SSD into RAM**, not DS4 streaming. DS4 streaming
remains attractive only with NVMe media and a quiet Metal machine (the 36 GB M4 Max
reports), and should be re-tested there before being promised.

## Planner eval result (3 tasks, 3 mock tools, ds4 on internal NVMe)

| task | tool calls | invalid | followed up | answered | time | tokens |
|---|---|---|---|---|---|---|
| sites needing intervention | 33 | 0 | yes | no (step budget hit) | 50 min | 25.8k |
| chat explains low attendance? | 10 | 0 | yes | no (step budget hit) | 19 min | 12.9k |
| volunteer effort vs attendance | 5 | 0 | yes | **yes, correct** (used real canned numbers per site) | 14 min | 4.8k |

Read: **tool-call discipline is excellent** - 48/48 structurally valid calls, correct
tools, real arguments, evidence-driven follow-ups, and the one completed answer
faithfully used the returned numbers. The weaknesses are (a) knowing when to stop
gathering (2/3 tasks explored past an 8-step budget instead of answering) and (b) speed:
14-50 minutes per task at this box's contended 1.4 tok/s floor - even trebled on a quiet
M4 Metal, minutes not the proposal's <60 s.

## Verdict vs proposal section 6

- start reliably from external SSD: **no** on spinning USB (DNF), untested on NVMe-USB4.
- stay within memory: yes trivially (server RSS ~1 GiB; experts ride page cache).
- >= 1.5-2 tok/s: **no** here (1.44 floor, compute-contended); plausible on quiet M4.
- valid multi-step tool calls: **yes, 100%**.
- useful planner cycle < 60 s: **no** - minutes per cycle at best.

Recommendation: for the event kit on commodity drives, the big local brain is
**Qwen3.8-27B Q4 loaded whole into RAM** (111 s load from the same spinning drive,
4.05 tok/s CPU floor here, Metal upside on a Mac). DS4 streaming is a research track:
retest on NVMe-USB4 + quiet Apple Silicon before promising it; and any planner use needs
hard step budgets and answer-forcing prompts regardless of engine.
