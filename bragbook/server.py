"""The dashboard: your brag book as a live page at http://localhost:8642.

Only reachable from your own computer (it listens on 127.0.0.1 and rejects other hosts).
"""

import html
import threading
import time
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import parse_qs, quote, urlencode, urlparse

from bragbook import config, report, timeline, tracker
from bragbook.db import DB

PERIODS = [("today", "Today"), ("week", "This week"), ("month", "This month"),
           ("quarter", "This quarter"), ("year", "This year")]


def url(port: int) -> str:
    return f"http://localhost:{port}"


def _ago(ts: Optional[float]) -> str:
    if ts is None:
        return "nothing recorded yet"
    mins = int((time.time() - ts) // 60)
    if mins < 1:
        return "just now"
    if mins < 60:
        return f"{mins} min ago"
    if mins < 60 * 24:
        return f"{mins // 60}h ago"
    days = mins // (60 * 24)
    return f"{days} day{'s' if days > 1 else ''} ago"


def _status_html(db, tracking: bool, back: str) -> str:
    last = db.last_sample_ts()
    if not tracking:
        dot, text = "off", ("Tracker isn't running, so nothing new is being recorded. "
                            "Run <code>bragbook autostart install</code> to keep it on.")
        button = ""
    elif tracker.paused():
        dot, text = "paused", "Tracking is paused."
        button = _post_button("/resume", back, "Resume")
    else:
        dot, text = "on", f"Tracking is on · last activity {_ago(last)}"
        button = _post_button("/pause", back, "Pause 1 hour")
    return f'<div class="status"><span class="dot {dot}"></span><span>{text}</span>{button}</div>'


def _post_button(action: str, back: str, label: str) -> str:
    return (f'<form method="post" action="{action}"><input type="hidden" name="next" value="{html.escape(back)}">'
            f'<button class="linkbtn" type="submit">{label}</button></form>')


def _top(db, tracking: bool, back: str, view: str, flash: str) -> str:
    flash_html = f'<div class="flash">{html.escape(flash)}</div>' if flash else ""
    views = [("timeline", "/", "Timeline"), ("book", "/book", "Brag book")]
    tabs = "".join(f'<a href="{href}" class="{"on" if k == view else ""}">{label}</a>' for k, href, label in views)
    return f"""
{_status_html(db, tracking, back)}
{flash_html}
<form class="winform" method="post" action="/win">
  <input type="hidden" name="next" value="{html.escape(back)}">
  <label for="t">What did you move forward?</label>
  <input id="t" name="text" required autocomplete="off" placeholder="e.g. Got sign-off on the concourse wayfinding pilot">
  <div class="row">
    <input name="impact" autocomplete="off" placeholder="What changed? (optional)">
    <input name="tags" autocomplete="off" placeholder="Tags, comma separated (optional)">
    <button type="submit">Log win</button>
  </div>
</form>
<nav class="tabs views">{tabs}</nav>"""


def book_page(db, cfg, per: str, tracking: bool, flash: str = "") -> str:
    first, last, label = report.period(per)
    data = report.build(db, cfg, first, last, label)
    back = f"/book?p={per}"
    periods = "".join(f'<a href="/book?p={k}" class="{"on" if k == per else ""}">{v}</a>' for k, v in PERIODS)
    top = _top(db, tracking, back, "book", flash) + f'<nav class="tabs">{periods}</nav>'
    return report.to_html(data, top_html=top)


def timeline_page(db, cfg, day: date, tracking: bool, flash: str = "") -> str:
    back = f"/?d={day.isoformat()}"
    return timeline.page(db, cfg, day, top_html=_top(db, tracking, back, "timeline", flash))


class Handler(BaseHTTPRequestHandler):
    tracking = False
    port = 8642

    def log_message(self, *args):  # keep the tracker log quiet
        pass

    def _allowed(self) -> bool:
        # Block other websites (and DNS-rebinding tricks) from reaching your data.
        host = (self.headers.get("Host") or "").split(":")[0]
        if host not in ("localhost", "127.0.0.1"):
            return False
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).hostname not in ("localhost", "127.0.0.1"):
            return False
        return True

    def _per(self, query: dict) -> str:
        per = (query.get("p") or ["week"])[0]
        return per if per in dict(PERIODS) else "week"

    def _send(self, code: int, body: str, ctype="text/html; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _redirect(self, back: str, flash: str = ""):
        if not back.startswith("/") or back.startswith("//"):
            back = "/"
        if flash:
            back += ("&" if "?" in back else "?") + urlencode({"msg": flash}, quote_via=quote)
        self.send_response(303)
        self.send_header("Location", back)
        self.end_headers()

    def do_GET(self):
        if not self._allowed():
            return self._send(403, "Forbidden", "text/plain")
        parsed = urlparse(self.path)
        q = parse_qs(parsed.query)
        if parsed.path == "/health":
            return self._send(200, "bragbook", "text/plain")
        flash = (q.get("msg") or [""])[0][:300]
        db = DB(config.db_path())
        try:
            cfg = config.load()
            if parsed.path == "/book" or (parsed.path == "/" and "p" in q):
                body = book_page(db, cfg, self._per(q), self.tracking, flash)
            elif parsed.path == "/":
                try:
                    day = date.fromisoformat((q.get("d") or [""])[0])
                except ValueError:
                    day = date.today()
                body = timeline_page(db, cfg, min(day, date.today()), self.tracking, flash)
            else:
                return self._send(404, "Not found", "text/plain")
        finally:
            db.close()
        self._send(200, body)

    def do_POST(self):
        if not self._allowed():
            return self._send(403, "Forbidden", "text/plain")
        parsed = urlparse(self.path)
        length = min(int(self.headers.get("Content-Length") or 0), 20000)
        form = parse_qs(self.rfile.read(length).decode("utf-8", "replace"))
        field = lambda k: (form.get(k) or [""])[0].strip()
        back = field("next") or "/"

        if parsed.path == "/win":
            text = field("text")
            if not text:
                return self._redirect(back)
            tags = ",".join(t.strip() for t in field("tags").split(",") if t.strip())
            db = DB(config.db_path())
            try:
                db.add_win(text, field("impact"), tags)
                new = tracker.check_achievements(db, config.load(), notify=False)
            finally:
                db.close()
            msg = "🧾 Logged. Nice."
            if new:
                msg += " Unlocked: " + ", ".join(f"{u.achievement.emoji} {u.achievement.name}" for u in new)
            return self._redirect(back, msg)
        if parsed.path == "/pause":
            tracker.pause(60)
            return self._redirect(back, "Paused for an hour.")
        if parsed.path == "/resume":
            tracker.resume()
            return self._redirect(back, "Tracking resumed.")
        self._send(404, "Not found", "text/plain")


def make_server(port: int, tracking: bool) -> ThreadingHTTPServer:
    handler = type("BragBookHandler", (Handler,), {"tracking": tracking, "port": port})
    return ThreadingHTTPServer(("127.0.0.1", port), handler)


def start_background(port: int) -> Optional[ThreadingHTTPServer]:
    """Serve the dashboard from inside the tracker. Returns None if the port is taken."""
    try:
        srv = make_server(port, tracking=True)
    except OSError:
        return None
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def is_running(port: int) -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as r:
            return r.read() == b"bragbook"
    except Exception:
        return False
