#!/bin/bash
# codex exec (in a throwaway container, no host sandbox) with a given model on a task in a fresh workspace
# usage: cx_run.sh <model> <tag> <srcdir> "<task>" [extra-dir-to-copy]
M=$1; TAG=$2; SRC=$3; TASK=$4; EXTRA=$5
R=/home/beeps/src/github.com/bprashanth/io/benchmarks/runs/2026-08-23-harness-v1/$TAG
WS=$HOME/.cache/io-codex-ws/$TAG; rm -rf $WS; mkdir -p $WS/work $WS/home $R; cp -r $SRC/. $WS/work/; [ -n "$EXTRA" ] && cp -r $EXTRA/. $WS/work/
cat > $WS/home/config.toml <<CFG
model = "$M"
model_provider = "openrouter"
model_reasoning_effort = "${EFFORT:-low}"
approval_policy = "never"
sandbox_mode = "danger-full-access"
[model_providers.openrouter]
name = "OpenRouter"
base_url = "https://openrouter.ai/api/v1"
env_key = "OPENROUTER_API_KEY"
wire_api = "responses"
CFG
KEY=$(python3 -c "import json;print(json.load(open('/home/beeps/.config/idlisseus/openrouter.json'))['api_key'])")
start=$(date +%s)
timeout 1200 docker run --rm --name cx-$(echo $TAG | tr "/" "-") -e OPENROUTER_API_KEY="$KEY" -e CODEX_HOME=/home/ngo/.codex -v $WS/home:/home/ngo/.codex -v $WS/work:/work -w /work --memory 4g io-codex-harness \
  codex exec --skip-git-repo-check --ephemeral --dangerously-bypass-approvals-and-sandbox -C /work --json -o /work/.last.md "$TASK" < /dev/null > $R/events.jsonl 2> $R/stderr.txt
echo "exit=$? seconds=$(( $(date +%s) - start ))" > $R/meta.txt
[ -f $WS/work/.last.md ] && cp $WS/work/.last.md $R/last.md
python3 - "$R" <<'PY'
import json,sys,collections
R=sys.argv[1]; c=collections.Counter(); cmds=[]; usage=None
for line in open(f"{R}/events.jsonl"):
    try: e=json.loads(line)
    except Exception: continue
    t=e.get("type",""); c[t]+=1
    item=e.get("item") or {}
    if item.get("type")=="command_execution": cmds.append((item.get("exit_code"), (item.get("command") or "")[:150]))
    if t=="turn.completed": usage=e.get("usage")
with open(f"{R}/summary.txt","w") as f:
    f.write(json.dumps(dict(c))+"\n"+json.dumps(usage)+"\n")
    for ec,cmd in cmds: f.write(f"{ec}  {cmd}\n")
PY
ls -la $WS/work | grep -v "^total" > $R/workspace-files.txt
