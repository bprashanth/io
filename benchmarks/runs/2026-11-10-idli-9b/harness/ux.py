"""UX judging: what the person saw (their messages, the replies, the cards and their clicks; no tool details),
graded by a judge model with a fixed rubric, blind to which model wrote it.

  python harness/ux.py export <run dir> --models a,b --variants base,guards --reps 0 > batch files in <run>/ux/
  python harness/ux.py judge <run dir>      (codex exec on each batch file; grades into <run>/ux/*.out.json)
  python harness/ux.py table <run dir>
"""
import glob
import json
import os
import random
import re
import subprocess
import sys

RUBRIC = """You are grading a chat assistant ("Idli") used by an analyst at an Indian NGO to find spreadsheets in their
Google Drive and ask questions about them. The assistant shows clickable cards; numbers must come from the data.
Each conversation below shows what the person saw: their messages, the assistant's replies, cards (question,
options) and what they clicked. You don't see the data; judge only the experience.

For each conversation give:
- score 1-5: 5 = feels like a capable colleague: short, natural, clear next step, answers what was asked;
  3 = gets there but with friction (an unneeded question, repeats, slightly robotic or long);
  1 = confusing, wrong turn, ignores the person, loops, or leaves them stuck.
- flags (any that apply): "too_long", "robotic", "unneeded_question", "ignores_request", "confusing",
  "repeats", "leaks_internals" (file paths, tool or id names the person shouldn't see; a chart image link is fine),
  "stuck" (no clear way forward), "contradicts".
- note: one short sentence on the main problem (or "fine").
Reply with JSON only: {"<conversation key>": {"score": n, "flags": [...], "note": "..."}, ...}"""


def visible(log):
    lines = []
    for t in log["turns"]:
        inp = t.get("input") or {}
        if t.get("skipped"):
            continue
        if not t.get("via_card"):
            if inp.get("user"):
                lines.append("PERSON: " + inp["user"])
            elif inp.get("pick"):
                lines.append("PERSON (typed, no card was shown): " + re.sub(r"[\\^$()|?*+\[\]]", "", inp["pick"]).split("|")[0])
        for e in t["events"]:
            if e["type"] == "model" and e.get("text"):
                txt = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"[chart image: \1]", e["text"])
                lines.append("IDLI: " + txt[:1200])
            elif e["type"] == "card":
                c = e.get("card") or {}
                for q in (c.get("questions") or [])[:2] if isinstance(c.get("questions"), list) else []:
                    if isinstance(q, dict):
                        opts = [o.get("label") if isinstance(o, dict) else str(o) for o in (q.get("options") or [])]
                        lines.append(f"IDLI CARD: {str(q.get('question'))[:400]} OPTIONS: {opts}")
                ans = re.findall(r'"="(.*?)"', e.get("answer") or "")
                lines.append("PERSON CLICKED: " + (", ".join(ans) if ans else "(closed the card)"))
    return "\n".join(lines)


def export(run, models, variants, reps):
    out_dir = os.path.join(run, "ux" + os.environ.get("UX_TAG", ""))
    os.makedirs(out_dir, exist_ok=True)
    convs = []
    for m in models:
        for v in variants:
            for p in sorted(glob.glob(os.path.join(run, m, v, "*.json"))):
                r = int(re.search(r"-r(\d+)\.json$", p).group(1))
                if r not in reps:
                    continue
                log = json.load(open(p))
                convs.append((f"{m}|{v}|{log['conv']}|r{r}", visible(log)))
    random.Random(1).shuffle(convs)  # mix models in each batch: the judge can't anchor on one
    keymap = {}
    for b in range(0, len(convs), 12):
        batch = convs[b:b + 12]
        body = []
        for j, (k, txt) in enumerate(batch):
            anon = f"c{b + j:04d}"
            keymap[anon] = k
            body.append(f"### {anon}\n{txt}")
        with open(os.path.join(out_dir, f"batch{b // 12:03d}.txt"), "w") as f:
            f.write(RUBRIC + "\n\n" + "\n\n".join(body))
    with open(os.path.join(out_dir, "keys.json"), "w") as f:
        json.dump(keymap, f, indent=1)
    print(len(convs), "conversations in", (len(convs) + 11) // 12, "batches")


def judge(run):
    out_dir = os.path.join(run, "ux" + os.environ.get("UX_TAG", ""))
    for p in sorted(glob.glob(os.path.join(out_dir, "batch*.txt"))):
        outp = p[:-4] + ".out.json"
        if os.path.exists(outp):
            continue
        last = p[:-4] + ".last.txt"
        cmd = ["codex", "exec", "-s", "read-only", "-C", out_dir, "-o", last,
               "Read the file " + os.path.basename(p) + " in this folder and do exactly what it says. Reply with the "
               "JSON only."]
        cmd.insert(2, "--skip-" + "git-repo-check")
        subprocess.run(cmd, capture_output=True, text=True, timeout=1200, stdin=subprocess.DEVNULL)
        try:
            txt = open(last).read()
            got = json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
            with open(outp, "w") as f:
                json.dump(got, f, indent=1)
            print(os.path.basename(p), len(got))
        except Exception as e:
            print(os.path.basename(p), "failed", e)


def table(run):
    out_dir = os.path.join(run, "ux" + os.environ.get("UX_TAG", ""))
    keys = json.load(open(os.path.join(out_dir, "keys.json")))
    agg = {}
    for p in glob.glob(os.path.join(out_dir, "*.out.json")):
        for anon, g in json.load(open(p)).items():
            if anon not in keys or not isinstance(g, dict):
                continue
            m, v, conv, r = keys[anon].split("|")
            a = agg.setdefault((m, v), {"scores": [], "flags": {}})
            a["scores"].append(g.get("score", 0))
            for fl in g.get("flags") or []:
                a["flags"][fl] = a["flags"].get(fl, 0) + 1
    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump({f"{m}|{v}": a for (m, v), a in agg.items()}, f, indent=1)
    for (m, v), a in sorted(agg.items()):
        s = a["scores"]
        top = sorted(a["flags"].items(), key=lambda x: -x[1])[:4]
        print(f"{m:22} {v:9} n={len(s):3} mean {sum(s) / len(s):.2f}  >=4: {sum(1 for x in s if x >= 4) / len(s):.0%}  "
              + ", ".join(f"{k} {n}" for k, n in top))


if __name__ == "__main__":
    cmd, run = sys.argv[1], os.path.abspath(sys.argv[2])
    if cmd == "export":
        args = dict(zip(sys.argv[3::2], sys.argv[4::2]))
        export(run, args["--models"].split(","), args["--variants"].split(","),
               [int(x) for x in args.get("--reps", "0").split(",")])
    elif cmd == "judge":
        judge(run)
    else:
        table(run)
