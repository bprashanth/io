# Official Census connector handoff and split journey

The final screening scenario asks the system to find official 2011 district
population online. The counted Antigravity result got every number right but
exported three false Census record links that resolved to unrelated 1961
monographs, scoring 78. The counted Cline/Qwen run failed before a page. A prior
DeepSeek Web plus Qwen run completed genuine official-source discovery and
scored 91, but used 830.346 model seconds plus 101.464 tool seconds.

This phase tested the post-discovery optimization separately. Catalog 42526 and
its A‑01 workbook URL, previously discovered by the DeepSeek run, were
revalidated live. Both returned HTTP 200 on 2026-08-20. The downloaded workbook
SHA‑256 was `6b649697ed5993da834b674173dab68e1ef9abb97e234155a80884c2fa4584f5`,
exactly matching the previously retained A‑01 bytes. A new bounded connector
accepts official Census URLs and district names, allowlists the host, retains
the workbook and retrieval manifest, selects district-total rows and creates a
traceable analysis table. It is explicitly not general web search.

The first split replay kept only Patna and Gaya on a turn that also asked which
of all three districts was largest, and assigned unit percent to the exact
population gap. Unit binding and a ranking-plus-gap scope rule were added. The
second replay completed all four turns without repair in four Qwen 3.8 27B Low
calls: 95.797 model seconds, USD 0.01495195, 6,368 prompt, 3,846 completion and
2,789 reasoning tokens.

The result preserves Patna 5,838,465, Gaya 4,391,418 and Nalanda 2,877,653;
Patna largest; the exact 1,447,047-person gap; and 58.38, 43.91 and 28.78 lakh.
Every row carries Census year 2011, publisher, A‑01 table, live catalog and
direct workbook URL. The URLs are clickable and preserved in the downloaded
CSV. Chromium found no runtime errors, external asset requests or desktop
overflow.

Human inspection found that long lakh-axis labels were clipped on the left even
though the browser checks passed. The renderer gutter was widened and all four
screenshots were rerun. The final post-discovery score is 98.5, but it is an
ablation rather than an apples-to-apples web-discovery score. The emerging
route is: common allowlisted official connector first, fast validated planner
and renderer next, then a bounded web-capable fallback only when no connector
matches.
