"""Start here chat: the index starts empty, and after drive_index it moves through its phases, one per status
check (each drive_index_wait / drive_index_status call), then is done. The real tools and texts are used;
only the index's state file is scripted (and the build itself is the tools' own dry-run switch)."""
import os


def apply(mcp, tools):
    from lib import driveindex as di
    from sites.google import tools as g
    open(os.path.splitext(di.DB)[0] + ".dryrun", "w").close()
    os.remove(di.DB)  # not indexed yet
    phases = [{"phase": "starting"}, {"phase": "listing", "files": 140, "folders_opened": 12, "folders_left": 9},
              {"phase": "reading", "peeked": 30, "to_read": 64}, {"phase": "summarising", "summarised": 80,
                                                                       "to_summarise": 212},
              {"phase": "done", "files": 212, "seconds": 171}]
    st = {"started": False, "n": 0}

    def status():
        if not st["started"]:
            return {"phase": "none"}
        p = phases[min(st["n"], len(phases) - 1)]
        st["n"] += 1
        return dict(p)

    real_index = g.t_drive_index

    def t_drive_index():
        out = real_index()
        st["started"] = True
        return out

    di.status = status
    g.time.sleep = lambda s: None  # drive_index_wait polls; no real waiting in the benchmark
    mcp.TOOLS["drive_index"] = (t_drive_index,) + tuple(mcp.TOOLS["drive_index"][1:])
