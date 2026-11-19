# CLI choices: one grammar for every capability

2026-11-19. Written with the follow-up benchmark (`benchmarks/runs/2026-11-19-capability-cli-mapping/`, condition
4). It goes with [SANDBOXES.md](SANDBOXES.md) ("Capabilities as CLIs") and the p1 todo
`todos/idli-insights/p1/capability_versions.md`. Each choice is marked **[decided]** (the owner has said so, or the
benchmark settled it) or **[proposed]** (for the owner to discuss).

## The problem

People check a Mini by asking it small questions before they trust it with the whole workflow:
- "list my leads";
- "show me this morning's lead replies";
- "my meetings yesterday";
- "what's in the study folder?".

Nothing writes code at that point. The 9B, or idli-remote with consent, turns the question into a call that Idli
runs on the real data. How good the answer is depends on what the call can express, and on how easily a model can
fill it in.

The first benchmark (32 questions over the leads sandbox, 11 held out) compared today's menu with commands:

| | Today's menu | Commands with arguments | + man pages with examples |
|---|---|---|---|
| 9B, all questions | 78% | 88% | 97% |
| idli-remote, all questions | 81% | 90% | 94% |

Commands with arguments let the menu express the question. The examples teach the 9B how to fill the arguments in.
**[decided: build capabilities as commands]**

The owner's next point: if every command follows a grammar models already know (kubectl, gh), the models arrive
already knowing the shape. This document picks that grammar.

## What the references teach

**kubectl** (kubernetes.io, "kubectl" overview and conventions; `kubectl explain`)
- `kubectl [command] [TYPE] [NAME] [flags]`: one small set of verbs works on every resource type.
  - Read verbs: `get`, `describe`, `explain`.
  - Write verbs: `create`, `apply`, `delete`, `patch`.
- **Take:**
  - **verb first:** the action is the first thing a model chooses;
  - **resources are things you can list;**
  - `get` with no name lists, with a name shows one;
  - **`explain TYPE` is the documentation for a resource,** generated from its schema;
  - **`--dry-run`** previews what a write would do;
  - **label selectors (`-l key=value`)** narrow any list in the same way.
- **Reject:**
  - `get` doing double duty for one item and many. We split it into `list` and `get`, as gh does, because a model
    has to choose between the two anyway and a separate word is clearer;
  - the long tail of special verbs (`rollout`, `taint`, `cordon`).

**gh, the GitHub CLI** (`gh pr list`, `gh help formatting`)
- `gh pr list --author X --label Y --state open --limit 30 --search Q --json fields --jq expr`.
- **Take:**
  - `list` takes filters as flags;
  - **`--limit` with a stated default;**
  - **`--search`** for free words;
  - **`--json` output** so the next step can use it.
- **Reject:**
  - noun-first ordering (`gh pr list`). It's the more common order in CLIs (clig.dev says so), but kubectl's verb
    first suits us better. Our first step is "is this a read or a write?", and that should be the first word.
    **[proposed: the follow-up benchmark could test noun-first too]**

**clig.dev** (Command Line Interface Guidelines)
- **Take:**
  - **lead help with examples:** "users tend to use examples over other forms of documentation". This matches the
    benchmark: examples gave the 9B its last 7 to 9 points;
  - **prefer flags to positional arguments:** clearer, and new input can be added without breaking old use;
  - **use the standard flag names** (`--dry-run`, `--json`, `--force`, `--limit`), so they can be guessed;
  - **be consistent with verbs across object types;**
  - **don't have ambiguous or similarly named commands** (their example: `update` against `upgrade`);
  - **no catch-all subcommand, no arbitrary abbreviations;**
  - **confirm before anything dangerous,** and make the dangerous confirmation hard to give by accident.
- **Reject:**
  - interactive prompts inside commands. Idli asks the person in the chat, never in the command.

**GNU and POSIX argument conventions**
- **Take:**
  - **long options everywhere,** spelled the same in every program (`--verbose` means one thing);
  - `--` ends the options.
- **Reject:**
  - short one-letter flags. They save typing for people, but cost models clarity. We keep long names only, except
    `-o`.

**docker**
- Management commands per object type (`docker container ls`, `docker image rm`) replaced the old flat commands
  (`docker ps`, `docker rmi`). The lesson is that a flat set of commands gets messy as it grows, and one consistent
  verb and noun pair stays readable.

**aws**
- **Take:**
  - **`--cli-input-json`** and **`--generate-cli-skeleton`**: every command can take its whole input as JSON, and
    can print a blank template of that input. That's what a model or a script wants.
- **Reject:**
  - service-specific verbs like `describe-instances` and `list-buckets`. Hundreds of distinct commands, each its own
    name, is what we want to avoid.

## The grammar

```
idli VERB RESOURCE [NAME] [flags]
```

### Verbs **[decided: a small fixed set; proposed: the exact words]**

| Verb | Kind | What it does |
|---|---|---|
| `list` | read | many items, short (one line each) |
| `get` | read | one item in full (an email's body, a file's content) |
| `explain` | read | what a resource, step or flag is: its man page, with examples |
| `judge` | read (domain) | the private 9B reads each item of a resource and answers a question: `--question Q --answers A,B,C` |
| `run` | read (preview) | `run step N` runs a Mini's steps 1 to N and shows step N; `run mini` runs the whole Mini. Both are previews |
| `draft` | write | an email draft. The person presses Send in Gmail |
| `book` | write | a calendar event, with guests |
| `send`, `post`, `delete` | write | not offered in any sandbox yet |

- **Every write verb previews by default.** It acts only with `--apply`, the reverse of kubectl's `--dry-run`, so a
  forgotten flag can't write. **[proposed]**
- **The mapper never sees write verbs.** idli-remote and the 9B get the read verbs only. Writes run when the
  person says "run it", or from a Mini's own steps. **[decided]**
- **`judge` and `run` are our only verbs outside the usual create, read, update, delete set,** as `logs` and
  `exec` are in kubectl. A judgement isn't a resource, so it gets its own verb rather than being forced into one.

### Resources

**Account resources**, built by our team:
- `mail`: emails. `list` shows date, sender, subject and first words; `get` shows one in full.
- `events`: meetings, with title, time, guests and declined or not. Busy times are events.
- `freetimes`: open slots in working hours. Its own flags are `--days`, `--minutes` and `--count`.
- `rows`: the rows of a sheet (`list rows SHEET_1`).
- `files`: Drive files, with name, kind, folder and last change. `get file FILE` gives the content (a PDF's text,
  or a spreadsheet's columns and first rows).

**Resources a Mini defines** are views over the account resources. They're the main win: they put the Mini's own
words into the grammar. **[proposed]**
- In the leads Minis:
  - `leads` is the people on the leads sheet;
  - `replies` is mail from leads, with calendar notices left out.
- So "this morning's lead replies" becomes `idli list replies --since 2026-11-19`, almost word for word.
- A view is declared in the Mini (a name, one line, and what it expands to). That's data, not code.

### Shared flags: the same meaning on every resource **[proposed]**

| Flag | Meaning |
|---|---|
| `--since DATE`, `--until DATE` | YYYY-MM-DD, both days included. Events use these too, not `--start`/`--end` |
| `--search WORDS` | any of the words appear (gh's `--search`) |
| `--where KEY=VALUE` | a field equals a value: `from=`, `guest=`, `in=`, `type=`, `shared=true`. The value `leads` means anyone on the Mini's leads list (kubectl's label selectors) |
| `--latest` | only the newest one |
| `--limit N` | at most N (default 10) |
| `--as ROLE` | which account: `me` by default, `lead` for the test contact (kubectl's `--context`) |
| `-o json` / `-o table` | JSON when piped, so steps chain; a table for people |
| `--apply` | write verbs only: actually do it |

### Steps and chains

A Mini is a chain of these commands. Each step is one line, and states the flags a question may change:

```
step 1: Read the leads sheet       idli list leads
step 2: Find their replies         idli list replies --since 2026-11-05      (may change: --since, --until, --search)
step 3: Read each reply            idli judge replies --question "did they agree to meet, and did they pick a time?" --answers picked,agreed,other
step 4: Draft open times           idli draft mail ... for each "agreed"     (a write: preview unless the person runs it)
step 5: Book the time they picked  idli book event ... for each "picked"
```

`run step 2 --since 2026-11-17` reruns steps 1 and 2 with that override and shows step 2. Glue between steps is
JSON on standard output, so the chain needs no code beyond the commands themselves. **[proposed]**

### `explain` is the man page **[decided by the benchmark]**

- **What it holds:** one line on what the command does, its flags, and two or three examples.
- **Examples use real dates.** Code fills them in from today's date at run time. With placeholders like `<today>`,
  the 9B copied the placeholder.
- **Examples never repeat a question people actually ask.** They teach the shape, not the answer.
- **No worked-out line of dates** ("this week is ..."). In the benchmark it made both mappers worse.

### Who may add what **[decided: the owner, 2026-11-19]**

| Who | May add |
|---|---|
| Sandbox Claude (inside) | flags on existing commands, add-only, within the sandbox's imports; chains of commands (Minis); views |
| The Builder (outside) | new read and transform commands, from trusted packages and sources; which commands a sandbox gets |
| Our team | write verbs, and new account resources or scopes |

A change to a shared command is copy-on-write inside the sandbox. New flags must be optional, with defaults that
keep the old behaviour. Each Mini is pinned to the version it was tested with, and the Builder promotes changes for
everyone (`todos/idli-insights/p1/capability_versions.md`).

## What the benchmark says about the grammar

The results are in [the benchmark's README](../benchmarks/runs/2026-11-19-capability-cli-mapping/README.md),
condition 4. They are summarised in the next section once the held-out set is scored.

## Open questions

- Verb first (kubectl) or noun first (gh, docker)?
- Should `get` with no name list items, as in kubectl, or stay strict?
- Where do views live: in the Mini's file, or as small commands the Builder writes?
- `--apply` against kubectl's `--dry-run`: preview by default is safer, but it's the opposite of what models have
  seen most often.
