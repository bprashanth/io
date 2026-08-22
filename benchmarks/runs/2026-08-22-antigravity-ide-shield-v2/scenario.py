import sys,time,json,subprocess; sys.path.insert(0,'/tmp/claude-1000/-home-beeps-src-github-com-bprashanth-io/4d6cd2ae-5f0d-422f-8aac-b2d7198f209b/scratchpad/gui')
from ide import *
G='/tmp/claude-1000/-home-beeps-src-github-com-bprashanth-io/4d6cd2ae-5f0d-422f-8aac-b2d7198f209b/scratchpad/gui'
msg, tag, limit, probes = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4:]
def approve(pg):
    for sel in ("text=Run Alt+Enter", "button:has-text('Run')", ".monaco-button:has-text('Run')", "text=Accept all", "text=Send all"):
        try:
            loc=pg.locator(sel).first
            if loc.count() and loc.is_visible(): loc.click(timeout=2000); time.sleep(1); return 1
        except Exception: pass
    return 0
with sync_playwright() as pw:
    b,pg=workbench(pw)
    if msg != "-": send(pg, msg)
    t0=time.time(); oks=0; last=None; stable=0; n=0
    while time.time()-t0 < limit:
        time.sleep(6); approve(pg); txt=chat_text(pg); tail=txt[-3000:]
        if 'Privacy shield' in tail and 'Reply' in tail[-900:] and 'ok' not in tail[-60:].lower():
            n+=1; pg.screenshot(path=f'{G}/{tag}-review{n}.png'); send(pg,'ok'); oks+=1; last=None; stable=0; time.sleep(8); continue
        if txt==last: stable+=6
        else: stable=0; last=txt
        if stable>=30 and ('shield:' in tail[-500:] or 'Worked for' in tail[-400:]): break
    pg.screenshot(path=f'{G}/{tag}-final.png')
    wire=subprocess.run(['curl','-s','http://127.0.0.1:8765/shield/last-request'],capture_output=True,text=True).stdout
    hits={p: wire.lower().count(p.lower()) for p in probes}
    print(json.dumps({"tag":tag,"secs":int(time.time()-t0),"ok_replies":oks,"status":[x for x in status_items(pg) if 'calls' in x],"wire_hits":hits}))
    print(txt[-1200:]); done()
