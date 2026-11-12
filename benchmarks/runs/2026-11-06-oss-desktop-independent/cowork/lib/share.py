"""Share what Idli learned (a file skill: its form, checks and charts) with someone else who has the app.

One bundle format, several ways to move it (see share_ways in sites/files/tools.py and docs/idli-sharing.md):
  a .idli file (send it any way you like), a Google Drive link, a hidden tab inside the shared sheet, a short code.

A bundle is a zip: manifest.json + skill/<the skill folder>. The skill was written by Claude against a fake copy, so
it carries no rows of the person's data; the only real words in it are labels the person chose to share when
teaching (category values, spelling maps). The manifest lists them, so the sender sees them before sharing and the
receiver before installing.

  pack(skill_id) -> {"path", "manifest"}       inspect(path) -> manifest + problems       install(path) -> result
"""
import base64
import datetime as dt
import hashlib
import io
import json
import os
import re
import shutil
import zipfile

from lib import filekit as fk
from lib import formkit as fm

FORMAT = "idli-share/1"
KEEP = re.compile(r"^(skill\.json|tests\.json|mock\.xlsx|charts/[\w.-]+\.(py|json))$")  # no rendered SVGs, no caches
MAX_FILE = 5 * 1024 * 1024
OUT_DIR = os.path.join(os.environ.get("IDLI_HOME") or os.path.expanduser("~/idli-insights"), "shared")


def _skill(skill_id):
    sk = next((s for s in fk.load_skills() if s["id"] == skill_id or s.get("title") == skill_id), None)
    if not sk:
        raise ValueError(f"No skill '{skill_id}'. Skills: {[s['id'] for s in fk.load_skills()]}")
    return sk


def real_words(skill):
    """The real labels inside a skill (what someone could learn from it about the original file)."""
    out = []
    for tab, t in fm.tabs_of(skill).items():
        for col, c in (t.get("columns") or {}).items():
            if c.get("values"):
                out.append({"tab": tab, "column": c.get("label") or col, "values": [str(v) for v in c["values"]][:40]})
        for col, n in (t.get("normalize") or {}).items():
            if isinstance(n, dict) and isinstance(n.get("map"), dict) and n["map"]:
                out.append({"tab": tab, "column": col, "spelling_map": list(n["map"].items())[:40]})
    return out


def _manifest(skill, files, who=None):
    return {"format": FORMAT, "kind": "file-skill", "id": skill["id"], "title": skill.get("title") or skill["id"],
            "version": skill.get("version", 1), "made": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "from": who or "", "tabs": {t: sorted((v.get("headers") or [])) for t, v in fm.tabs_of(skill).items()},
            "measures": sum(len(v.get("measures") or []) for v in fm.tabs_of(skill).values()),
            "checks": sum(len(v.get("validations") or []) for v in fm.tabs_of(skill).values()),
            "charts": sorted(os.path.splitext(f)[0][7:] for f in files if f.startswith("charts/") and f.endswith(".py")),
            "real_words": real_words(skill),
            "files": {f: hashlib.sha256(b).hexdigest() for f, b in files.items()}}


def pack_bytes(skill_id, who=None, with_mock=True):
    """(zip bytes, manifest)."""
    sk = _skill(skill_id)
    root = sk["_dir"]
    files = {}
    for dirpath, _, names in os.walk(root):
        for n in names:
            rel = os.path.relpath(os.path.join(dirpath, n), root).replace(os.sep, "/")
            if not KEEP.match(rel) or (rel == "mock.xlsx" and not with_mock):
                continue
            p = os.path.join(dirpath, n)
            if os.path.getsize(p) <= MAX_FILE:
                with open(p, "rb") as f:
                    files[rel] = f.read()
    with open(os.path.join(root, "skill.json")) as f:
        skill = json.load(f)
    man = _manifest(skill, files, who)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(man, indent=1, ensure_ascii=False))
        for rel, b in sorted(files.items()):
            z.writestr("skill/" + rel, b)
    return buf.getvalue(), man


def pack(skill_id, out_path=None, who=None):
    data, man = pack_bytes(skill_id, who)
    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = out_path or os.path.join(OUT_DIR, f"{man['id']}-v{man['version']}.idli")
    with open(out_path, "wb") as f:
        f.write(data)
    return {"path": out_path, "manifest": man, "bytes": len(data)}


def _open(src):
    if isinstance(src, (bytes, bytearray)):
        return zipfile.ZipFile(io.BytesIO(src))
    return zipfile.ZipFile(src)


def inspect(src):
    """The manifest, plus problems that make the bundle unsafe or unusable (then install refuses)."""
    problems = []
    try:
        z = _open(src)
    except (zipfile.BadZipFile, OSError) as e:
        return {"manifest": None, "problems": [f"not an Idli bundle ({type(e).__name__})"]}
    with z:
        try:
            man = json.loads(z.read("manifest.json"))
        except (KeyError, ValueError):
            return {"manifest": None, "problems": ["no manifest: not an Idli bundle"]}
        if man.get("format") != FORMAT or man.get("kind") != "file-skill":
            problems.append(f"unknown bundle format {man.get('format')!r}/{man.get('kind')!r}")
        if not re.fullmatch(r"[\w.-]{1,80}", str(man.get("id") or "")):
            problems.append("bad skill id")
        names = [n for n in z.namelist() if n != "manifest.json"]
        for n in names:
            rel = n[len("skill/"):] if n.startswith("skill/") else None
            if rel is None or not KEEP.match(rel) or ".." in rel:
                problems.append(f"unexpected file {n!r}")
            elif hashlib.sha256(z.read(n)).hexdigest() != (man.get("files") or {}).get(rel):
                problems.append(f"{rel} doesn't match the manifest")
        if "skill/skill.json" not in names:
            problems.append("no skill.json")
        else:
            try:
                sk = json.loads(z.read("skill/skill.json"))
                if sk.get("id") != man.get("id"):
                    problems.append("skill id differs from the manifest")
            except ValueError:
                problems.append("skill.json is not JSON")
    return {"manifest": man, "problems": problems}


def install(src, replace=False):
    """Install a bundle into this Idli's skills. Same version already here: nothing to do. Older here: replaced
    (the old one kept in archive/skills). Newer here: refused unless replace."""
    got = inspect(src)
    man = got["manifest"]
    if got["problems"]:
        return {"installed": False, "why": "; ".join(got["problems"]), "manifest": man}
    have = next((s for s in fk.load_skills() if s["id"] == man["id"]), None)
    if have and have.get("version", 1) == man["version"] and not replace:
        return {"installed": False, "already": True, "why": f"Idli already has {man['title']} (version "
                f"{man['version']}).", "manifest": man}
    if have and have.get("version", 1) > man["version"] and not replace:
        return {"installed": False, "why": f"Idli has a newer {man['title']} (version {have.get('version', 1)} vs "
                f"{man['version']}).", "manifest": man}
    dest = os.path.join(fk.SKILLS_DIR, man["id"])
    kept = None
    if os.path.exists(dest):
        kept = os.path.join(os.environ.get("IDLI_HOME") or os.path.expanduser("~/idli-insights"), "archive", "skills",
                            f"{man['id']}-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}")
        os.makedirs(os.path.dirname(kept), exist_ok=True)
        shutil.move(dest, kept)
    with _open(src) as z:
        for n in z.namelist():
            if n.startswith("skill/"):
                p = os.path.join(dest, n[len("skill/"):])
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, "wb") as f:
                    f.write(z.read(n))
    with open(os.path.join(dest, "shared_from.json"), "w") as f:
        json.dump({"from": man.get("from"), "made": man.get("made"), "installed": dt.datetime.now().isoformat()}, f)
    return {"installed": True, "id": man["id"], "title": man["title"], "version": man["version"], "replaced": kept,
            "manifest": man}


def to_text(data):
    """Bundle bytes as text (a sheet cell, a code server)."""
    return base64.b64encode(data).decode()


def from_text(text):
    return base64.b64decode(re.sub(r"\s+", "", text))


def describe(man):
    """One paragraph for a card: what the bundle carries, and the real words in it."""
    words = man.get("real_words") or []
    w = ("; real words inside: " + "; ".join(
        f"{x['column']}: " + ", ".join((x.get("values") or [k for k, _ in x.get("spelling_map", [])])[:6])
        for x in words[:4])) if words else "; no real words from the original file inside"
    who = f" from {man['from']}" if man.get("from") else ""
    return (f"{man['title']} (version {man['version']}{who}): {man['measures']} measures, {man['checks']} checks, "
            f"{len(man['charts'])} charts for files with tabs {', '.join(man['tabs'])}{w}.")
