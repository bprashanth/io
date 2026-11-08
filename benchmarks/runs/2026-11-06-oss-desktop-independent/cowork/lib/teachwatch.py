"""Wait for a Teach chat to finish (it writes done.json in the request folder), then tell the Idli chat.

Started detached by teach_send:  teachwatch.py <request_dir> <idli_agent_id> <paseo_cli>
Gives up after 3 hours. Afterwards, switches the app back to the Idli chat if the
Teach chat asks it to (a go_back file).
"""
import json
import os
import subprocess
import sys
import time

rdir, agent, paseo = sys.argv[1:4]
done = os.path.join(rdir, "done.json")
for _ in range(3 * 3600 // 10):
    if os.path.exists(done):
        time.sleep(2)
        try:
            with open(done) as f:
                d = json.load(f)
        except (OSError, ValueError):
            d = {}
        msg = (f"Teaching finished: {d.get('summary') or 'the file skill is ready'}. "
               "Open the file again with file_open and continue with my question.")
        subprocess.run([paseo, "send", "--no-wait", agent, msg], timeout=60,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        break
    time.sleep(10)

# The Teach chat asks "Go back to Idli?" on a card; on yes it touches go_back here (it runs sandboxed and can't
# reach the app itself). Wait up to 30 minutes for that, then switch the app to the Idli chat.
go = os.path.join(rdir, "go_back")
if os.path.exists(done):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for _ in range(30 * 60 // 2):
        if os.path.exists(go):
            from lib import uiswitch
            uiswitch.show_agent(agent)
            break
        time.sleep(2)
