# Overnight field note: looking for a local-size alternative to Antigravity

## What we learnt so far

Qwen 3.8 27B is the first model we tried that is good enough to continue as a
serious Antigravity alternative for ordinary NGO dashboard work. In the one
strict test run through the actual products, VS Code with Cline and Qwen 3.8
27B did better than Antigravity on the overall preliminary score. It was better
at carrying follow-up requests into the website and at making a page that still
worked on a narrow screen. Antigravity was faster and made the better download,
but it answered one follow-up only in chat and left the website unchanged.

That is a promising screening result, not yet proof of equivalence. The actual-
product comparison contains one small CSV case, one run per setting, and
unblinded visual review. The older five-case screen used the official command-
line products rather than the graphical products people will use. Both systems
failed badly on three of those five cases. We have therefore found a finalist
and improved the test, but we have not finished the benchmark.

We also learnt that the model is only part of the result. The same 27B model was
unreliable and slow inside one version of Cline, very strong but extremely
expensive inside DeepSeek Web, and strong again in the current Cline extension.
The surrounding tool decides how often the model is called, what context is
resent, whether follow-ups change the page, and whether downloads and sources
are checked. Any conclusion must name the whole combination, not just the
model.

## The practical goal

The goal is not to win a general coding contest. It is to give a small NGO a
general-purpose way to understand an unfamiliar file without needing a data
analyst or programmer beside them.

A user may bring a CSV, Excel workbook or PDF, or ask the tool to find an
official dataset online. They ask in short, ordinary Indian English. The tool
should make a simple website, let them select years or districts, answer later
questions by changing that same website, explain what the data can and cannot
show, retain its sources, and download the current table.

Antigravity is the reference because it is a real end-user product that already
does this kind of work. The candidate is VS Code with Cline pointing to a model
whose weights can eventually run on our own DGX. During this first phase the
candidate models came through OpenRouter. That let us compare models without
first downloading and serving every set of weights. It does **not** establish
that a quantised local copy will behave identically. Local replay is a later,
separate claim.

The target is a candidate no more than seven points behind Antigravity on a
frozen 100-point score, with no extra serious data or citation failures. We will
also show five- and ten-point interpretations. A much smaller model may be
considered up to fifteen points behind only when the loss is presentation or
minor convenience, not wrong data, invented sources, unsafe explanations or a
broken website. That would be called an operational trade-off, not equivalence.

## What the benchmark asks

We rejected the first idea of generating 100 random spreadsheets and grading
screenshots. It would have been easy to scale and difficult to trust. Instead,
we planned 20 small cases: 12 for development and eight untouched cases for the
final comparison. So far, five development cases and one machinery-only smoke
case are built. The remaining planned cases and all holdout cases have not been
run.

The built development screen covers:

1. a clean district health CSV;
2. a two-sheet maternal-health Excel workbook;
3. a short digital PDF with a health table;
4. an aggregate livelihoods file where the user asks for a cause the file
   cannot establish; and
5. finding official district population data on the Census website.

Most local files are deterministic synthetic aggregates. They contain no real
people or private health data. The Census task uses the live official web. The
fixtures are intentionally ordinary rather than trick questions. Later cases
will add missing cells, merged headers, formulas, scanned PDFs, joins, spelling
differences, suppressed values and boundary changes.

The [full planned bank](../benchmarks/cases/CASE_BANK.md) shows what is built and
what is still only planned. Every built case has its exact messages, input
hashes, provenance and a machine-readable answer key in
[`benchmarks/cases/`](../benchmarks/cases/). A few examples show the tone:

> one csv is there. make simple website for 4 antenatal checkup coverage by
> district and year. i should select year and compare districts. show source
> and how rate is calculated

> compare gaya and nalanda. tell change from 2021 to 2023 in percentage points

> why gaya is below nalanda? dont guess if this file cannot tell

> this pdf has one district health table. make simple website for facility
> delivery coverage by year and district. i should select year and compare.
> show source page and table number

> find official govt data online for 2011 total population of patna gaya and
> nalanda districts in bihar. make simple website to compare them. show exact
> source link and census year. dont use blogs

The tiny [smoke conversation](../benchmarks/cases/smoke-001/case.json) has only
three messages: make an immunisation website, restrict it to 2023 and identify
the lowest district without guessing why, then add a download. Its job is to
prove that installation, conversation memory, website launch, browser checks
and downloads work. Its score is never allowed into the final aggregate.

## How an answer was checked

We did not mark a run correct because the HTML looked plausible. Each input has
known totals and formulas. Case-specific scripts compare the visible values and
downloaded rows with those answers. A wrong number, fabricated source, broken
site, misleading control, or download that materially disagrees with the page
is a serious failure that visual polish cannot cancel.

Every generated website was actually served and opened in Chromium through
Playwright. We saved a desktop image and a 390-pixel-wide image, exercised the
controls, captured browser and console errors, and inspected the downloaded
file. The narrow view caught several pages whose right-hand columns were
invisible on a phone-sized screen. We also recorded external requests and, for
the development cases, checked whether the site survived when CDNs were
blocked. The connected workshop view remains the main score; offline behaviour
is reported separately.

The 100 points are weighted toward substance: 35 for data and calculations, 15
for working controls and downloads, 15 for sources, 10 for honest uncertainty,
10 for usefulness to an NGO user, 10 for visual quality and 5 for time and
cost. The exact [scoring file](../benchmarks/config/scoring.json), case checkers,
screenshots, transcripts, generated sites and downloads are retained under
[`benchmarks/`](../benchmarks/README.md).

Visual scores so far are preliminary human judgements made with the system
identity visible. They checked hierarchy, chart choice, units, labels,
contrast, clipping, phone layout and whether a non-technical user could
understand the page. A later confidence run needs repeated and preferably
blinded review. A visual judge will never be allowed to override a numerical
checker.

## Getting the machinery to work

The first part of the night was mostly about making the comparison real rather
than quietly substituting a convenient API script for the products.

We installed the official ARM64 Antigravity and Cline command-line clients on
the Ubuntu server. The first measured command-line versions were Antigravity
1.1.15 and Cline 3.0.55. Cline needed a current local Node installation. Docker
was already present, and Playwright worked after its ARM64 Chromium payload was
available.

Cline's first configuration route did not work. Environment variables that
looked as though they should select OpenRouter and Qwen were ignored, and Cline
fell back to its own provider. Passing provider flags selected the right type
of provider, but an isolated Cline profile still needed its own OpenRouter
authentication. We fixed that through Cline's supported authentication path.
This is worth retaining because merely setting two environment variables is not
a reproducible setup.

The next failure was conversation resume. Cline's JSON command accepted a
conversation ID but silently discarded the later prompt. We reproduced this in
positional and piped forms before treating it as a known client bug. Those runs
are invalid because the model never saw the follow-up. We moved the unattended
runner to Cline's ACP session interface, which kept one live Cline process and
conversation across turns.

The proposed OpenRouter slug, `qwen/qwen3.8-27b`, really exists and the
downloadable Qwen weights were verified. However, Cline 3.0.55's model catalogue
was stale. An early attempt silently selected Claude Sonnet 5 instead. That run
was discarded, and every later runner was changed to fail if the resolved model
did not match the requested model. For Qwen 3.8 we used Cline's normal custom
OpenAI-compatible provider field with OpenRouter's URL and the exact free-text
model name. This is also the route we can later point at a local LiteLLM, vLLM
or similar endpoint.

The default OpenRouter route once went idle before the first edit. We retained
that as a provider failure, then tried the `:nitro` route, which asks OpenRouter
to favour throughput while still resolving to the same Qwen model. Provider
routing varied across Reka, AkashML, Chutes and Alibaba during the night. One
counted Census run ended when an Alibaba moderation response appeared inside an
otherwise successful stream. A later retry showed that the model could do the
task, but it stayed excluded because retries cannot replace a counted zero.
DeepSeek Web also hit a Reka rate limit on a PDF turn and recovered in the same
conversation. These hosted routing failures may disappear locally, but local
serving will not automatically repair a wasteful agent loop.

The first Cline smoke did make a correct dashboard. It exceeded Cline's
recommended 6,000-character editor write limit, then recovered by splitting the
edit. Later, one multiline command was damaged by VS Code terminal integration
and the agent recovered through a temporary script. These are product rough
edges, not model correctness failures, but they matter to time and workshop
friction.

Antigravity authentication also worked over SSH, first through its printed
login flow and later through a localhost OAuth callback forwarded from the
laptop. A host-only Antigravity smoke then showed that starting it inside a
temporary directory did not contain it: the agent could search unrelated files
under the user's home directory. We therefore built a shared outer container
with the same Python, Node, Excel, PDF and shell tools for both command-line
agents, and used another read-only, resource-capped container for every
generated site. The first container image was itself invalidated because it
lacked `ps`; Antigravity could not check its preview process and blocked on a
foreground server. We added process inspection, rebuilt the image, and excluded
all of that first screening batch.

## The early smoke results

The equivalent container smoke was encouraging. Antigravity's command-line
default resolved to Gemini 3.7 Flash High and scored 89/100. Cline with Qwen 3.8
27B scored 92/100. Antigravity made the richer page and a correct download, but
left 2022 content visible after the user asked for 2023 only and invented
performance bands that were not in the data. Qwen followed the 2023 request and
rendered cleanly, but its CSV omitted year and source.

We also tested low reasoning because a smaller reasoning budget sounded like a
possible speed and cost saving. It was not. The low-effort Cline run made 38
model calls, resent 810,226 prompt tokens, took 540 seconds and cost about
USD 0.44. Its page was correct, but its download still omitted year and its
narrow table still overflowed slightly. This negative result is useful: fewer
reasoning tokens do not help if the surrounding agent repeatedly resends and
rechecks the whole workspace.

Two same-size but older-generation Qwen diagnostics were also kept out of model
selection. Qwen 3.5 27B completed the conversation with correct numbers but had
overlapping labels and a clipped phone table. Qwen 3.6 27B wrapped JavaScript in
literal script tags inside a `.js` file, causing a syntax error and blank
visuals. These runs warned us not to treat parameter count alone as a clean
quality ladder.

The first full CSV pilot then compared five turns and scored Antigravity 88 and
Cline/Qwen 86. We excluded both runs because we used their output to clarify
which wide and long download layouts were acceptable and whether online CDN
requests belonged in the main browser condition. A calibration run cannot also
be counted as if the rules were frozen beforehand.

## The counted five-case screen

The first frozen screen used the official command-line products, one run on
each of the five built development cases. It is the only five-case product
aggregate from the night:

| Case | Antigravity CLI | Cline CLI + Qwen 3.8 27B | What happened |
| --- | ---: | ---: | --- |
| Health CSV | 84 | 78 | Both mostly worked; each had a different follow-up/control defect. |
| Health Excel | 89 | 93 | Both were accurate; Qwen left the final page and download in better shape but was much slower. |
| Health PDF | 0 | 95 | Antigravity's model request returned 403; Qwen made a strong cited page. |
| Programme interpretation | 10 | 73 | Antigravity ignored the file and invented data and causes; Qwen refused to guess but chose the wrong employment denominator. |
| Official Census discovery | 78 | 0 | Antigravity had correct values but false links to unrelated 1961 catalogue records; Qwen hit the moderation/provider failure before making a page. |
| **Total** | **261/500** | **339/500** | **Qwen led by 15.6 points per case on average.** |

The machine-readable [counted result](../benchmarks/results/screening-v2-counted.json)
gives the components and failure gates. The important conclusion is not that
Qwen won. Both systems had a serious failure in three of five cases. Qwen/Cline
passed a relative screening comparison and failed absolute readiness.

Opening the sites changed our understanding. An Antigravity Census dashboard
looked excellent but linked to unrelated records. Its programme dashboard also
looked polished at first glance, but contained invented data and had a script
error that left it blank. Qwen's PDF page was restrained and genuinely strong;
its programme page leaked raw CSS above the header. Visual quality was useful
evidence, but could never stand in for source and arithmetic checks.

The command-line comparison also exposed why it could not be the final claim.
Antigravity wrote some work to its own scratch space, sometimes returned an
`ERROR` object despite a zero process exit, and one Excel run needed a recorded
preview-process intervention. Cline made between 21 and 50 model calls for
complete cases and repeatedly wrote its own browser-like tests. We needed a
sample through the actual editor products before saying what NGO participants
would experience.

## Searching below 27B

We used a frozen futility rule so an obviously failing small model would not
consume the entire question bank. After at least three paired cases, a model
could be stopped if it trailed by 20 points with no plausible recovery or had
two extra serious failures.

Qwen 3.5 9B in default Cline met both rules. Across the programme, CSV and Excel
cases it scored 41/300 against Antigravity's 183/300 and failed to produce a
usable website in all three cases. We did not waste runs on PDF and web
discovery. This rules out that exact 9B model and Cline combination, not every
possible 9B model or better harness.

Qwen3 14B was tried through DeepSeek Web after that harness was working. It was
fast and could use tools, but its first ordinary page silently omitted two of
four districts and attached an invented `example.org` link to the synthetic
source. The frozen early-stop rule ended the remaining turns. These are data
and citation failures, so the optional fifteen-point visual-quality allowance
does not apply.

The 9B, 14B and 27B models come from different Qwen generations and were tried
through different exact harnesses. We therefore cannot draw a smooth parameter
curve or say every model between 15B and 26B fails. The honest bracket is only:
for the tested combinations, viable size is above 14B and at or below 27B.

We did not move upward to an 80B, 122B or DeepSeek V4-class model. The 27B
candidate had already shown enough capability to justify a downward search.
Larger models remain fallback candidates if the repeated actual-product suite
later shows that 27B cannot hold the required margin.

## Trying a different harness

Cline's repeated calls and wrong programme denominator raised a separate
question: was the 27B model weak, or was the surrounding agent using it badly?
We tested the published DeepSeek Harness as a diagnostic. This was deliberately
kept separate from the Antigravity-versus-Cline product score.

The first Python composition with a general NGO instruction scored 92 on the
programme case and handled both plausible denominator definitions. It still
failed to put all later answers back into the page. It also ran with broad host
permissions and read listings outside the staged workspace, so later use moved
to an outer container and the actual DeepSeek Web interface.

DeepSeek Web without a guardrail repeated Cline's wrong denominator. A first
general guardrail made it ask two sensible questions, but the operator's
answers selected the benchmark definitions. That 87-point run is diagnostic,
not a strict replay. The second guardrail avoided test-specific hints. It told
the agent to show all definitions calculable from the file when a metric was
ambiguous, keep each follow-up in the durable page, resolve phrases such as
“this table” from the immediate conversation, and export raw counts, units,
formulas and sources.

With that generic instruction, DeepSeek Web and Qwen 3.8 27B scored 92, 86, 93,
83 and 91 on the five development cases: mean 89, with no serious failure. It
was the strongest multi-case capability result of the night. The Census run
found two valid official catalogues, retained the workbooks, showed exact and
lakh values, kept follow-ups in the page and exported official URLs. We opened
both source links and verified the downloaded workbook hash independently.

The cost makes it unsuitable as-is. Five conversations took 264 model steps,
3.08 million uncached input tokens, 7.86 million cache-read tokens and 222,000
output tokens. OpenRouter reported USD 5.64 for 263 successful generations.
The Census case alone took 81 steps and about 830 seconds of model time to
verify three district values. This track proves that the 27B model can do the
work with better guidance. It does not prove that current Cline matches
Antigravity, nor that DeepSeek Web is ready for 10–20 simultaneous NGO users.
Its Windows packaging is also still unverified.

## Finally testing the actual graphical products

We installed Antigravity IDE 1.107.0 and VS Code 1.134.0 with Cline extension
4.1.10 on the headless ARM64 server. They ran inside a virtual display. We
controlled their real Electron windows through the browsers' debugging
connection, rather than replacing them with a direct API call.

The in-app browser integration had no available browser session on this SSH
host. Antigravity's own browser helper also failed because its Playwright 1.57
ARM64 driver URL returned 404. We therefore used independent Playwright to open
and grade the websites. This still tests the generated page, but it is a
recorded workaround rather than Antigravity proving its own preview.

Antigravity onboarding required separate consent for Google to use interaction
data for product and model improvement. The user explicitly authorised that
mandatory checkbox; promotional email remained off. The first post-consent
attempt then failed on a one-time account-settings decoding error. After a
restart, the interface displayed Gemini 3.5 Flash Low, but its request carried
no actual selected model and the language server rejected it. Opening the model
selector initialised the usable default as Gemini 3.6 Flash High. We cancelled
a diagnostic request before it changed files, then began a fresh conversation
and workspace for the valid run. The failed warm-ups were retained and not
scored.

The actual Cline extension was configured through its onboarding with
OpenRouter, `qwen/qwen3.8-27b`, Act mode and Xhigh reasoning. A second fresh run
used Medium reasoning. All three systems received the same 324-byte CSV with
the same SHA-256 and the exact same three messages in one conversation. We
opened every final page and download.

| Actual product run | Score | Visual /10 | Time | Follow-up changed page | Download identifies year/source | Phone-width overflow |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| Antigravity / Gemini 3.6 Flash High | 80.5 | 7.5 | 595 s | No | Yes | 238 px |
| VS Code + Cline / Qwen 3.8 27B Xhigh | 91.2 | 9.2 | 844 s | Yes | No: year missing | 0 px |
| VS Code + Cline / Qwen 3.8 27B Medium | 85.5 | 8.6 | 893 s | Yes | No: year missing | 0 px |

Antigravity made the most elaborate desktop page and the only standalone
download containing district, year, numerator, denominator, percentage and
source. It was also roughly four minutes faster than Cline Xhigh. Its chat
correctly said Purnia was lowest in 2023 at 76%, 760 of 1,000, and did not
invent a reason.

However, that second turn changed no files. The website still contained seven
visible references to 2022 and did not show the lowest-district finding. At
phone width it clipped chart and table content. It invented High, Moderate and
Low bands, called percentage-point changes percentages, and described a
weighted value as an ordinary average. It also depended on remote Chart.js and
font files.

Cline Xhigh made a calmer, fully responsive page and actually converted it to a
2023-only view after the follow-up. The visible numbers and source were right,
and the lowest district was carried into the durable page. Its CSV contained
the right three districts and values but omitted the year, so it could not
stand alone after download. The three-turn run used 412,921 input tokens,
25,616 output tokens and cost USD 0.251. It also needed repeated human approval
of commands.

Medium reasoning cost 17% less and emitted fewer output tokens, but took longer,
scored lower, invented colour thresholds and repeated the missing-year export.
Reasoning effort does not reduce the local model's weight memory. On this one
run, Medium was neither the quality winner nor an end-to-end speed improvement,
so Xhigh remains the quality setting for the next confidence tests.

The [paired actual-product record](../benchmarks/results/product-gui-smoke-v1-diagnostic.json)
is deliberately labelled diagnostic. The Cline runs reused an existing client
profile, Antigravity needed its model selector initialised, and every setting
was run only once with the reviewer aware of its identity. The result advances
27B/Xhigh. It does not yet justify the sentence “a local model is equivalent to
Antigravity.”

## What is included, excluded and stopped

This distinction prevents us from accidentally repeating failures or combining
incomparable evidence.

| Work | Status | Why |
| --- | --- | --- |
| Frozen five-case Antigravity CLI versus Cline/Qwen 27B | Counted development screen | Rules and case hashes were frozen before these runs. |
| Three-case Cline/Qwen 9B screen | Counted futility stop | It met both predeclared stop rules; PDF and web were intentionally not run. |
| DeepSeek Web 27B five-case result | Named diagnostic | Strong model-plus-harness evidence, but not the Cline product users were meant to receive. |
| Actual Antigravity and Cline GUI smoke | Paired diagnostic | Correct products and messages, but one case, one unblinded run and documented state deviations. |
| Tiny smoke runs | Excluded from headline results | They tested installation, sessions, browsers and downloads. |
| First CSV pilot | Excluded | Its output was used to alter accepted download shapes and browser network rules. |
| Screening v1 | Excluded | The shared image lacked process inspection and caused an environment/intervention defect. |
| Silent Claude fallback | Invalid | The requested Qwen model was never used. |
| Failed resume messages | Invalid | Cline discarded the user follow-up before any model call. |
| Default-route idle failure and Antigravity 403 | Product/provider failures | Preserved; no successful retry silently replaced a counted failure. |
| Successful Census retry | Diagnostic only | It proves conditional capability but cannot overwrite the earlier counted zero. |
| DeepSeek guardrail v1 with operator clarifications | Diagnostic only | The human answers made it a different conversation from the frozen prompts. |
| Qwen3 14B after one turn | Frozen early rejection | Half the districts and the real source were lost; continuing would waste calls. |

Two evaluator corrections were made after seeing DeepSeek Census output. The
checker had omitted one valid official Census catalogue and accepted only one
way to round a lakh conversion. Those accepted-answer rules were broadened
without modifying the generated page or CSV, and the changes are recorded in
the run metadata. Similar changes accepted normal wording for causal caveats
and `pt`/`pts` for percentage points. These are reasonable semantic fixes, but
they are also why this is development evidence rather than untouched holdout.

## Shortcuts and limits

We took practical shortcuts to get a trustworthy first answer overnight:

- OpenRouter stood in for a local inference server. No model was served on the
  DGX, and no quantisation, memory use, tokens per second or concurrent-user
  capacity was measured.
- Only five of the planned 20 substantive cases are built. The actual-product
  GUI comparison used only the tiny smoke case. No holdout case has run.
- Most inputs are synthetic aggregate fixtures. This gives exact answers and
  avoids private data, but it does not yet cover the messiness of real NGO
  spreadsheets and scanned documents.
- Scores and visual reviews are preliminary and unblinded. There are not yet
  three repetitions or a paired confidence interval.
- Command-line runs used strong outer-container isolation. The graphical smoke
  used fresh workspaces on the host under a virtual display because packaging
  both full editors into clean per-run containers would have delayed the
  apples-to-apples test. The observed paths and deviations are recorded.
- The Cline GUI profile was reused, although each conversation and workspace was
  fresh. Antigravity's usable default needed one model-selector initialisation.
- Antigravity did not expose token or price data. We observed 35 planner
  requests in its GUI run, but cannot make a fair cost comparison from that.
- OpenRouter providers changed underneath the same model name and produced an
  idle timeout, moderation stop and rate limit. Hosted reliability is therefore
  not a proxy for local reliability.
- DeepSeek Web's excellent score used a generic extra guardrail that the default
  Cline and Antigravity products did not receive. It answers a useful harness
  question, not the original product-equivalence question.

No Antigravity quota ceiling was measured. The material limits encountered
were missing cost/token reporting, the default-model initialisation bug, the
ARM64 browser-driver 404, Cline's resume and catalogue bugs, OpenRouter provider
variation, and the very large number of model calls made by both Cline ACP and
DeepSeek Web.

## How another person can reproduce the flow

The easiest way to understand the experience is an independent laptop install.
The server automation is useful for repeated measurement, but it is not yet a
one-command public runner.

On a laptop:

1. Check out or copy this repository and run
   `python3 benchmarks/scripts/verify_cases.py` to verify all retained input
   sizes and hashes.
2. Install the current Antigravity desktop application. Use a fresh folder
   containing only one case's `inputs/` files. Keep its normal model, mode and
   effort, but record both the model shown in the interface and the model that
   actually answers.
3. Install current VS Code and the Cline extension. In Cline onboarding choose
   OpenRouter, set the model exactly to `qwen/qwen3.8-27b`, choose Act mode and
   Xhigh reasoning for the current finalist. Use a different fresh folder with
   byte-identical inputs.
4. Copy the messages from that case's `case.json` one at a time into the same
   conversation. Do not reveal the oracle, benchmark output or the other
   product's files to either agent.
5. After each follow-up, check the website rather than accepting a correct chat
   sentence. Confirm that old years disappear when requested, summaries and
   controls agree, sources remain visible, and the downloaded table carries
   enough context to stand alone.
6. Serve the generated site using its documented command. For a plain static
   site, `python3 -m http.server 3000` from the generated workspace is enough.
   The smoke checker can then be run as:

   ```sh
   python3 benchmarks/scripts/check_smoke_001.py \
     http://127.0.0.1:3000 /tmp/smoke-checks.json \
     --phase final --expect-download
   ```

   The development cases have equivalent `check_dev_*.py` scripts. Save both
   desktop and 390-pixel screenshots and inspect the downloaded CSV directly.

For the SSH server route, Antigravity's printed web login can be opened on the
laptop. If the OAuth redirect uses a localhost port on the server, forward that
same port before signing in:

```sh
ssh -L <callback-port>:127.0.0.1:<callback-port> user@server
```

The graphical benchmark ran both editors inside an Xvfb virtual display and
kept their Electron debugging ports bound to localhost. That route is suitable
for Playwright/CDP automation, not the simplest human workshop experience. To
view a generated dashboard from the laptop, forward only its application port:

```sh
ssh -L 13000:127.0.0.1:<remote-app-port> user@server
```

Then open `http://127.0.0.1:13000` locally. A normal laptop install is preferable
for judging approval prompts, file selection and follow-up usability. The SSH
route is preferable for repeatable batches, clean containers and later access
to the DGX.

Do not use private beneficiary or patient data in either cloud product or
OpenRouter. Use these public/synthetic fixtures until the local serving path is
ready. Never copy API keys, OAuth logs or browser profiles into a run directory.

## What should happen next

First, freeze the corrected actual-product protocol. It must accept buttons,
tabs or dropdowns as valid controls; require a website change when the user
refers to the website; reject invented status bands and percentage/percentage-
point mistakes; require year and source in filtered downloads; and retain phone
and offline checks.

Then run the five ordinary built scenarios once through fresh Antigravity and
Cline GUI profiles. Fix only genuine runner/checker defects. If 27B remains
within the seven-point margin with no extra serious failures, freeze two more
repetitions and build the untouched holdout. Only then search intermediate
15B–26B models, because the present evidence does not tell us where inside that
gap capability changes.

After the hosted winner is fixed, serve the exact recorded model revision
locally behind a stable OpenAI-compatible endpoint such as LiteLLM in front of
vLLM or another suitable engine. Replay the same case bytes and messages. Record
quantisation, chat/tool template, context limits, GPU memory, speed and every
generated artifact. Only that phase can support the claim that the local model
matches the hosted result.

The recurring failures already suggest two later improvement paths. One is
better guidance and deterministic data tools: preserve raw counts, state metric
definitions, validate source identity, keep every follow-up in the page, and
verify exports. The other is targeted training on repeated failure patterns.
Training should wait until repeated and holdout runs show that a failure belongs
to the model rather than Cline, the provider or the checker. A small-to-large
router is also possible, but its escalation rule must be frozen without looking
at the answer key.

Finally, test 10–20-user concurrency only after quality and local replay are
settled. A local endpoint may remove OpenRouter failures and cost, but the 264-
step DeepSeek result shows that a wasteful harness can exhaust a DGX even when
the model itself fits.

This longer note should remain in the producer repository while the experiment
is moving. When the evidence is repeated and stable, Remembrancer can import
the append-only [chronology](../chronology/README.md), copy a compact evidence
cut, and turn this into a shorter field note for somebody returning weeks later.
