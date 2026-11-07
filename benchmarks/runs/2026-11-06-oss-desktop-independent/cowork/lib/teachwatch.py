"""Wait for a Teach chat to finish (it writes done.json in the request folder), then tell the Idli chat.

Started detached by teach_send:  teachwatch.py <request_dir> <idli_agent_id> <paseo_cli>
Gives up after 3 hours.
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
