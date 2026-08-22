import sys,time,json; sys.path.insert(0,'/tmp/claude-1000/-home-beeps-src-github-com-bprashanth-io/4d6cd2ae-5f0d-422f-8aac-b2d7198f209b/scratchpad/gui')
from ide import *
G='/tmp/claude-1000/-home-beeps-src-github-com-bprashanth-io/4d6cd2ae-5f0d-422f-8aac-b2d7198f209b/scratchpad/gui'
msg, shot, limit = sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv)>3 else 420
def approve(pg):
    n=0
    for sel in ("text=Run Alt+Enter", "button:has-text('Run')", "text=Accept all"):
        try:
            loc=pg.locator(sel).first
            if loc.count() and loc.is_visible(): loc.click(timeout=2000); n+=1; time.sleep(1)
        except Exception: pass
    return n
with sync_playwright() as pw:
    b,pg=workbench(pw)
    if msg != "-": send(pg, msg)
    t0=time.time(); last=None; stable=0; approvals=0
    while time.time()-t0 < limit:
        time.sleep(6); approvals+=approve(pg); txt=chat_text(pg); tail=txt[-2500:]
        if ('Privacy shield' in tail and 'Reply' in tail): break
        if txt==last: stable+=6
        else: stable=0; last=txt
        if stable>=30 and ('shield:' in tail or 'Worked for' in tail): break
    print(json.dumps({"secs":int(time.time()-t0),"approvals":approvals,"status":[x for x in status_items(pg) if 'calls' in x or 'Shield' in x]}))
    pg.screenshot(path=G+'/'+shot); print(txt[-1500:]); done()
