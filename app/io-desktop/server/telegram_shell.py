"""Telegram shell: a thin bot that speaks io's lanes. Runs as a thread inside the io service on the
user's laptop (long polling — no inbound port, no server). Every reply carries the reach and the
egress line, so a phone user sees the same honesty as the desktop.

Commands: /start, /reach [laptop|t4gc|frontier], /files, /why, /skills, /propose, /approve N, plain text = ask/build/page
"""

from __future__ import annotations

import json
import threading
import time
import traceback
import urllib.parse
import urllib.request

API = "https://api.telegram.org/bot{token}/{method}"


class TelegramShell:
    def __init__(self, token: str, svc) -> None:
        self.token = token
        self.svc = svc            # the io_service module (WS, run_ask, run_build, run_page, load_config, save_config, step...)
        self.offset = 0
        self.username = None
        self.running = False
        self.last_turn: dict = {}
        self.pending_cards: list[dict] = []
        self.thread: threading.Thread | None = None
        self.log: list[dict] = []

    # -------------------------------------------------- transport
    def call(self, method: str, **params):
        data = urllib.parse.urlencode({k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in params.items() if v is not None}).encode()
        req = urllib.request.Request(API.format(token=self.token, method=method), data=data)
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.load(r)

    def send(self, chat_id, text: str, mono: bool = False):
        chunks = [text[i:i + 3800] for i in range(0, len(text), 3800)] or [""]
        for ch in chunks:
            body = f"<pre>{html_escape(ch)}</pre>" if mono else html_escape_keep_b(ch)
            try:
                self.call("sendMessage", chat_id=chat_id, text=body, parse_mode="HTML")
            except Exception:  # noqa: BLE001
                self.call("sendMessage", chat_id=chat_id, text=ch)

    def send_document(self, chat_id, name: str, content: bytes, caption: str = ""):
        boundary = "----ioBoundary7f3"
        parts = [f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n",
                 f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption[:1000]}\r\n",
                 f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; filename=\"{name}\"\r\nContent-Type: text/html\r\n\r\n"]
        body = "".join(parts).encode() + content + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(API.format(token=self.token, method="sendDocument"), data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)

    # -------------------------------------------------- lifecycle
    def start(self) -> dict:
        me = self.call("getMe")
        self.username = me["result"]["username"]
        self.running = True
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()
        return {"username": self.username}

    def stop(self) -> None:
        self.running = False

    def loop(self) -> None:
        while self.running:
            try:
                r = self.call("getUpdates", offset=self.offset, timeout=25)
                for u in r.get("result", []):
                    self.offset = u["update_id"] + 1
                    msg = u.get("message") or u.get("edited_message")
                    if msg and msg.get("text"):
                        try:
                            self.handle(msg["chat"]["id"], msg["text"].strip(), msg.get("from", {}))
                        except Exception as exc:  # noqa: BLE001
                            traceback.print_exc()
                            self.send(msg["chat"]["id"], f"Something went wrong on the laptop: {str(exc)[:200]}")
            except Exception:  # noqa: BLE001
                traceback.print_exc()
                time.sleep(3)

    # -------------------------------------------------- conversation
    def reach_line(self, egress: dict | None) -> str:
        cfg = self.svc.load_config()
        reach = cfg.get("reach", "laptop")
        e = egress or {}
        return f"{reach.capitalize()} · {e.get('model', '')} · rows sent 0 · {e.get('seconds', 0)}s"

    def handle(self, chat_id, text: str, user: dict) -> None:
        svc = self.svc
        self.log.append({"at": time.strftime("%H:%M:%S"), "from": user.get("username") or user.get("first_name"), "text": text[:200]})
        cfg = svc.load_config()
        if text.startswith("/start"):
            folder = str(svc.WS.folder) if svc.WS.folder else "no folder open on the laptop yet"
            self.send(chat_id, f"io on {user.get('first_name', 'your')}'s laptop.\nFolder: {folder}\nReach: {cfg.get('reach', 'laptop')}\n\nAsk a question about the data, or say 'dashboard' / 'report' / 'form' / 'app'.\n/reach to change who may help · /files · /why · /skills · /propose")
            return
        if text.startswith("/reach"):
            arg = text.split(maxsplit=1)[1].strip().lower() if len(text.split()) > 1 else ""
            if arg in ("laptop", "t4gc", "frontier"):
                cfg["reach"] = arg
                svc.save_config(cfg)
            reach = cfg.get("reach", "laptop")
            who = {"laptop": f"the laptop-tier model ({cfg.get('model')}) — only column names leave the laptop, never rows",
                   "t4gc": f"the trusted sector server model ({cfg.get('t1_model')}) — column names and tokens, never rows",
                   "frontier": f"a frontier model ({cfg.get('t2_model')}) — column names and tokens, never rows"}[reach]
            self.send(chat_id, f"Reach is {reach}: {who}.\nChange with /reach laptop | t4gc | frontier")
            return
        if text.startswith("/files"):
            ts = [t for t in svc.WS.tables if t.get("table")]
            self.send(chat_id, "\n".join(f"• {t['file']}{' › ' + t['sheet'] if t.get('sheet') else ''} → {t['rows']} rows × {len(t['columns'])} cols" + (f"  [skills: {', '.join(t['why']['skills'])}]" if t.get('why', {}).get('skills') else "") for t in ts) or "No folder open on the laptop.")
            return
        if text.startswith("/why"):
            t = self.last_turn
            if not t:
                self.send(chat_id, "Nothing answered yet.")
                return
            sql = t.get("sql") or "\n".join(p.get("sql", "") for p in (t.get("plan") or {}).get("panels", [])[:4])
            self.send(chat_id, f"Lane: {t.get('lane')}\nTables: {', '.join(t.get('tables_used') or [])}\nSkills fired: {', '.join(t.get('skills_fired') or []) or 'none'}\n\nQuery run on the laptop:\n{sql}", mono=False)
            return
        if text.startswith("/skills"):
            self.send(chat_id, "\n".join(f"• {s['name']} ({s['kind']}, {s.get('_layer')}): {s.get('description', '')[:80]}" for s in svc.WS.skills) or "No skills.")
            return
        if text.startswith("/propose"):
            if not cfg.get("astronaut"):
                self.send(chat_id, "Astronaut mode is off on the laptop. Turn it on in Settings first.")
                return
            tier = "t2" if "frontier" in text else "t1"
            model = cfg.get("t2_model") if tier == "t2" else cfg.get("t1_model")
            self.send(chat_id, f"Consent: a remote model ({model}) will read your questions and queries from this folder — never your data values — and propose skills. Working…")
            with svc.WS.lock:
                r = svc.run_compact(cfg, tier)
            self.pending_cards = r["cards"]
            if not self.pending_cards:
                self.send(chat_id, "Nothing to propose yet — ask more questions first, especially ones that went wrong.")
                return
            lines = [f"{i + 1}. {c['name']} ({c['kind']}) — {c.get('description', '')[:120]}" + ("  ⚠ contains data values, blocked" if c.get("leaks") else "") for i, c in enumerate(self.pending_cards)]
            self.send(chat_id, f"{len(self.pending_cards)} proposal(s) from {r['log_lines']} logged question(s) ({r['seconds']}s):\n" + "\n".join(lines) + "\n\nReply /approve N to save one; it applies from the next question.")
            return
        if text.startswith("/approve"):
            try:
                n = int(text.split()[1]) - 1
                c = self.pending_cards[n]
            except Exception:  # noqa: BLE001
                self.send(chat_id, "Say /approve 1 (the number from the list).")
                return
            if c.get("leaks"):
                self.send(chat_id, "That proposal contains data values and cannot be saved.")
                return
            with svc.WS.lock:
                p = svc.skillmod.save_skill({k: v for k, v in c.items() if k not in ("fires_on", "leaks")}, "folder", svc.WS.folder)
                svc.WS.load(svc.WS.folder, keep_history=True)
            self.send(chat_id, f"Saved skill {c['name']} ({p.name}). It fires from your next question; /why shows when it did.")
            return
        if not svc.WS.tables:
            self.send(chat_id, "No folder is open on the laptop. Open one in the io app first.")
            return
        # plain question → lanes
        lane = "page" if (svc.PAGE_WORDS.search(text) and not svc.re.search(r"\b(dashboard|report|summar\w*)\b", text, svc.re.I)) else "build" if svc.BUILD_WORDS.search(text) else "ask"
        self.send(chat_id, {"ask": "Writing one query on the laptop…", "build": "Planning a page; every number will be computed here…", "page": "Writing a page; your rows never leave the laptop…"}[lane])
        svc.PROGRESS.clear()
        svc.FIRED.clear()
        with svc.WS.lock:
            turn = svc.run_page(text, cfg) if lane == "page" else svc.run_build(text, cfg) if lane == "build" else svc.run_ask(text, cfg)
            turn["id"] = str(len(svc.WS.history) + 1)
            turn["at"] = time.strftime("%H:%M:%S")
            turn["skills_fired"] = sorted(set(svc.FIRED) | {n for t in svc.WS.tables for n in (t.get("why") or {}).get("skills", []) if t.get("table") in (turn.get("tables_used") or [])})
            svc.WS.history.append(turn)
            svc.WS.turns[turn["id"]] = turn
            svc.log_turn(turn)
        self.last_turn = turn
        if turn.get("error"):
            self.send(chat_id, f"Couldn't answer: {turn['error'][:300]}\n{self.reach_line(turn.get('egress'))}")
            return
        if lane == "ask":
            self.send(chat_id, table_text(turn["columns"], turn["rows"]), mono=True)
            note = (" ⚠ " + turn["scope_note"]) if turn.get("scope_note") else ""
            self.send(chat_id, f"{turn['rowcount']} row(s) · from {', '.join(turn.get('tables_used') or [])}{note}\n{self.reach_line(turn.get('egress'))}\n/why for the query")
        else:
            with svc.WS.lock:
                page = svc.page_with_data(turn) if lane == "page" else svc.render_page_now(turn)
            title = (turn.get("plan") or {}).get("title") or "page"
            self.send_document(chat_id, f"io-{lane}.html", page.encode(), caption=f"{title} — open on any phone/laptop. {self.reach_line(turn.get('egress'))}")
            if lane == "build":
                failed = turn.get("panels_failed") or []
                self.send(chat_id, f"{turn.get('panels')} panel(s), every figure computed on the laptop{(' · ' + str(len(failed)) + ' could not be computed') if failed else ''}. /why for the queries.")


def html_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def html_escape_keep_b(s: str) -> str:
    return html_escape(s)


def table_text(columns: list[str], rows: list[dict], max_rows: int = 15, max_cols: int = 6) -> str:
    cols = columns[:max_cols]
    data = rows[:max_rows]

    def fmt(v):
        if isinstance(v, float):
            return f"{v:,.2f}".rstrip("0").rstrip(".")
        if isinstance(v, int) and not isinstance(v, bool):
            return f"{v:,}"
        return "" if v is None else str(v)
    widths = [min(max(len(c), *(len(fmt(r.get(c))) for r in data)) if data else len(c), 22) for c in cols]
    line = lambda vals: " | ".join(str(v)[:w].ljust(w) for v, w in zip(vals, widths))  # noqa: E731
    out = [line(cols), "-+-".join("-" * w for w in widths)] + [line([fmt(r.get(c)) for c in cols]) for r in data]
    if len(rows) > max_rows:
        out.append(f"… {len(rows)} rows in all")
    if len(columns) > max_cols:
        out.append(f"({len(columns) - max_cols} more column(s) not shown)")
    return "\n".join(out)
