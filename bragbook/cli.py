"""bragbook: the command line."""

import argparse
import os
import sys
import time
import webbrowser
from datetime import date, datetime, timedelta
from pathlib import Path

from bragbook import achievements, analysis as A, autostart, config, report, sensors, tracker
from bragbook.categorize import categorize, extract_artifact
from bragbook.db import DB


def _db():
    return DB(config.db_path())


def cmd_track(args):
    cfg = config.load()
    if args.interval:
        cfg["sample_seconds"] = args.interval
    try:
        tracker.run(_db(), cfg, verbose=args.verbose)
    except KeyboardInterrupt:
        print("\nStopped. Nice work today.")


def cmd_check(args):
    cfg = config.load()
    print(f"Data folder: {config.home()}")
    win = sensors.active_window()
    idle = sensors.idle_seconds()
    if win:
        cat = categorize(win[0], win[1], cfg["categories"])
        print(f"Active window: {win[0]} | {win[1] or '(no title)'}")
        print(f"  → category: {cat}; working on: {extract_artifact(win[0], win[1], cat) or '–'}")
        if not win[1] and sensors.SYSTEM == "Darwin":
            print("  No window title. Allow your terminal under System Settings → Privacy & Security → "
                  "Accessibility (and Screen Recording on newer macOS).")
    else:
        print("Couldn't read the active window.")
        if sensors.SYSTEM == "Linux":
            print("  Install xdotool (X11 only; Wayland sessions aren't supported yet).")
    print(f"Idle detection: {'%.0fs since last input' % idle if idle is not None else 'unavailable (idle time will be counted)'}")
    print("Tracking is paused." if tracker.paused() else "Tracking is active (when `bragbook track` is running).")


def cmd_win(args):
    text = " ".join(args.text).strip()
    impact = args.impact or ""
    if not text:
        try:
            text = input("What did you move forward? ").strip()
            if text and not impact:
                impact = input("What changed because of it? (optional, Enter to skip) ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 1
    if not text:
        print("Nothing logged.")
        return 1
    db = _db()
    when = None
    if args.date:
        when = datetime.combine(date.fromisoformat(args.date), datetime.now().time()).timestamp()
    win_id = db.add_win(text, impact, ",".join(args.tag or []), ts=when)
    print(f"🧾 Logged win #{win_id}. That's {db.win_count()} in the book.")
    tracker.check_achievements(db, config.load(), notify=False)  # prints any new badges


def cmd_wins(args):
    db = _db()
    first, last, label = _range(args)
    start, end = A.day_range(first, last)
    rows = db.wins_between(start, end)
    print(f"Wins: {label}")
    if not rows:
        print("  None yet. `bragbook win` to add one.")
    for w in rows:
        impact = f"  → {w['impact']}" if w["impact"] else ""
        print(f"  #{w['id']:<4} {report.md(A.to_date(w['ts'])):<7} {w['text']}{impact}")


def cmd_unwin(args):
    print("Deleted." if _db().delete_win(args.id) else f"No win #{args.id}.")


def cmd_today(args):
    db, cfg = _db(), config.load()
    d = report.build(db, cfg, date.today(), date.today(), "Today")
    print(f"Today so far · {'  '.join(f'{v} {k.lower()}' for k, v in d.stats.items())}")
    for c, s in d.categories[:6]:
        print(f"  {c:<22} {A.hours(s)}")
    if d.badges:
        print("Earned today: " + "  ".join(f"{g['a'].emoji} {g['a'].name}" for g in d.badges))
    if not d.wins:
        print("No win logged yet today. `bragbook win` takes 10 seconds.")


def cmd_timeline(args):
    from bragbook import timeline
    db, cfg = _db(), config.load()
    day = date.fromisoformat(args.date) if args.date else date.today()
    start, end = A.day_range(day, day)
    print(f"{day:%A}, {report.mdy(day)}\n")
    print(timeline.to_text(timeline.sessions(A.load_samples(db, cfg, start, end))))


def cmd_badges(args):
    db, cfg = _db(), config.load()
    first_ts = db.first_sample_ts()
    if first_ts is not None:
        achievements.evaluate(db, cfg, A.to_date(first_ts), date.today())
    counts, latest = {}, {}
    for u in db.all_unlocks():
        counts[u["achievement_id"]] = counts.get(u["achievement_id"], 0) + 1
        latest[u["achievement_id"]] = u
    print("Trophy case\n")
    for period, title in (("day", "Daily"), ("week", "Weekly"), ("milestone", "Milestones")):
        print(title)
        for a in achievements.ACHIEVEMENTS:
            if a.period != period:
                continue
            if a.id in counts:
                n = f" ×{counts[a.id]}" if counts[a.id] > 1 else ""
                print(f"  {a.emoji} {a.name}{n}: last earned {latest[a.id]['day']}")
            else:
                print(f"  🔒 {a.name}: {a.description}")
        print()


def _range(args):
    if getattr(args, "start", None):
        first = date.fromisoformat(args.start)
        last = date.fromisoformat(args.end) if args.end else date.today()
        return first, last, f"{report.md(first)} – {report.md(last)}"
    return report.period(getattr(args, "period", None) or "week")


def cmd_report(args):
    db, cfg = _db(), config.load()
    first, last, label = _range(args)
    data = report.build(db, cfg, first, last, label)
    if args.format == "md":
        text = report.to_markdown(data)
        if not args.output:
            print(text)
            return
    else:
        text = report.to_html(data)
    out = Path(args.output) if args.output else config.home() / "reports" / f"bragbook-{first}-to-{last}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"Brag book written to {out}")
    if args.format == "html" and not args.no_open:
        webbrowser.open(out.resolve().as_uri())


def cmd_dashboard(args):
    from bragbook import server
    port = config.load()["dashboard_port"]
    link = server.url(port)
    if server.is_running(port):
        print(f"Opening {link}")
        webbrowser.open(link)
        return
    print(f"The tracker isn't running, so serving the dashboard from here: {link}")
    print("Leave this window open while you use it (Ctrl+C to stop). "
          "Tip: `bragbook autostart install` keeps it available all the time.")
    srv = server.make_server(port, tracking=False)
    if not args.no_open:
        webbrowser.open(link)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print()


def cmd_pause(args):
    tracker.pause(args.minutes)
    print(f"Paused for {args.minutes:g} minutes." if args.minutes else "Paused until `bragbook resume`.")


def cmd_resume(args):
    tracker.resume()
    print("Tracking resumed.")


def cmd_forget(args):
    n = _db().delete_samples_since(time.time() - args.minutes * 60)
    print(f"Deleted {n} activity samples from the last {args.minutes:g} minutes.")


def cmd_config(args):
    path = config.write_defaults(force=args.reset)
    print(f"Settings file: {path}")
    print("Edit it to change categories, privacy exclusions, workday hours or the sample interval.")


def cmd_autostart(args):
    print(autostart.install() if args.action == "install" else autostart.remove())


def cmd_demo(args):
    from bragbook import demo
    home = Path(args.home) if args.home else config.home() / "demo"
    if home.exists():
        for f in ("bragbook.db",):
            (home / f).unlink(missing_ok=True)
    home.mkdir(parents=True, exist_ok=True)
    os.environ["BRAGBOOK_HOME"] = str(home)
    db = DB(config.db_path())
    demo.seed(db)
    first = date.today() - timedelta(days=21)
    args.start, args.end, args.format, args.output = first.isoformat(), None, "html", None
    print(f"Seeded 3 weeks of demo data in {home} (your real data is untouched).")
    cmd_report(args)


def build_parser():
    p = argparse.ArgumentParser(prog="bragbook",
                                description="Track your computer activity and turn it into achievements and a brag book.")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("track", aliases=["start"], help="run the tracker (leave it running)")
    s.add_argument("--interval", type=int, help="seconds between samples (default 15)")
    s.add_argument("-v", "--verbose", action="store_true", help="print each sample")
    s.set_defaults(fn=cmd_track)

    s = sub.add_parser("check", help="test that window tracking works on this computer")
    s.set_defaults(fn=cmd_check)

    s = sub.add_parser("win", help="log a win (run with no text to be prompted)")
    s.add_argument("text", nargs="*")
    s.add_argument("-i", "--impact", help="the result: what changed, for whom, by how much")
    s.add_argument("-t", "--tag", action="append", help="tag (repeatable)")
    s.add_argument("--date", help="YYYY-MM-DD, if it happened on an earlier day")
    s.set_defaults(fn=cmd_win)

    for name, fn, hlp in (("wins", cmd_wins, "list wins"), ("report", cmd_report, "build your brag book")):
        s = sub.add_parser(name, help=hlp)
        g = s.add_mutually_exclusive_group()
        for per in ("today", "week", "month", "quarter", "year"):
            g.add_argument(f"--{per}", dest="period", action="store_const", const=per)
        s.add_argument("--from", dest="start", help="YYYY-MM-DD")
        s.add_argument("--to", dest="end", help="YYYY-MM-DD")
        if name == "report":
            s.add_argument("--format", choices=["html", "md"], default="html")
            s.add_argument("-o", "--output", help="where to save it")
            s.add_argument("--no-open", action="store_true", help="don't open it in the browser")
        s.set_defaults(fn=fn)

    s = sub.add_parser("unwin", help="delete a win by number")
    s.add_argument("id", type=int)
    s.set_defaults(fn=cmd_unwin)

    s = sub.add_parser("dashboard", aliases=["open"], help="open your brag book page in the browser")
    s.add_argument("--no-open", action="store_true", help=argparse.SUPPRESS)
    s.set_defaults(fn=cmd_dashboard)

    sub.add_parser("today", help="quick look at today").set_defaults(fn=cmd_today)
    s = sub.add_parser("timeline", help="your day as a timeline of sessions")
    s.add_argument("--date", help="YYYY-MM-DD (default: today)")
    s.set_defaults(fn=cmd_timeline)
    sub.add_parser("badges", aliases=["achievements"], help="your trophy case").set_defaults(fn=cmd_badges)

    s = sub.add_parser("pause", help="pause tracking (privacy mode)")
    s.add_argument("minutes", nargs="?", type=float, default=0, help="minutes (default: until resumed)")
    s.set_defaults(fn=cmd_pause)
    sub.add_parser("resume", help="resume tracking").set_defaults(fn=cmd_resume)

    s = sub.add_parser("forget", help="delete recent activity")
    s.add_argument("minutes", type=float, help="delete the last N minutes")
    s.set_defaults(fn=cmd_forget)

    s = sub.add_parser("config", help="create/show the settings file")
    s.add_argument("--reset", action="store_true", help="overwrite with defaults")
    s.set_defaults(fn=cmd_config)

    s = sub.add_parser("autostart", help="start tracking automatically at login")
    s.add_argument("action", choices=["install", "remove"])
    s.set_defaults(fn=cmd_autostart)

    s = sub.add_parser("demo", help="see a sample brag book built from fake data")
    s.add_argument("--home", help=argparse.SUPPRESS)
    s.add_argument("--no-open", action="store_true")
    s.set_defaults(fn=cmd_demo)
    return p


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # emoji on Windows consoles
        except Exception:
            pass
    args = build_parser().parse_args(argv)
    return args.fn(args) or 0
