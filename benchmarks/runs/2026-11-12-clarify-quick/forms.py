"""Open fixture files through the real product (fake Drive) and dump their forms."""
import json, os, sys, tempfile
S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["BENCH_COWORK"] = "/home/beeps/src/github.com/bprashanth/io/benchmarks/runs/2026-11-06-oss-desktop-independent/cowork"
os.environ["IDLI9B_FIXTURES"] = "/home/beeps/src/github.com/bprashanth/io-evals-1111/benchmarks/runs/2026-11-10-idli-9b/fixtures"
sys.path.insert(0, os.path.join(S, "harness"))
import idli
FILES = ["Volunteer register 2025.xlsx", "Household survey 2025.xlsx", "Field programme tracker Q3.xlsx",
         "Tech reimbursement form (Responses).xlsx", "MGNREGA works Valparai 2019-2023.xlsx", "Road kill survey 2011-12.xlsx"]

def setup():
    mcp = idli.setup(tempfile.mkdtemp(prefix="clarify-"))
    from sites.files import tools as ft
    opened = {}
    for f in idli._drive()["files"]:
        if f["name"] in FILES:
            r, err = idli.call(mcp, "file_get", {"link": "https://docs.google.com/spreadsheets/d/" + f["id"] + "/edit"})
            opened[f["name"]] = r["file"]
    return mcp, ft, opened

if __name__ == "__main__":
    mcp, ft, opened = setup()
    for name, rel in opened.items():
        e = ft.files().open(rel)
        print("#####", name, "->", rel)
        for f in e["forms"].values():
            b = ft._brief(f)
            b["filters"] = {x["column"]: ({"label": x["label"], "values": x.get("values")} if x["kind"] == "choice"
                            else {"label": x["label"], "kind": x["kind"]}) for x in f["filters"]}
            print(json.dumps(b, ensure_ascii=False))
