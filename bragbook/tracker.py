"""The background loop: sample the active window, then check for new achievements now and then."""

import time
from datetime import date, datetime, timedelta

from bragbook import achievements, analysis as A, config, sensors
from bragbook.categorize import is_excluded

EVALUATE_EVERY = 10 * 60


def pause_file():
    return config.home() / "paused_until"


def paused() -> bool:
    path = pause_file()
    if not path.exists():
        return False
    try:
        until = float(path.read_text().strip() or 0)
    except ValueError:
        until = 0
    if until and time.time() >= until:
        path.unlink(missing_ok=True)
        return False
    return True


def pause(minutes: float = 0):
    """Pause tracking. 0 minutes = until `bragbook resume`."""
    until = time.time() + minutes * 60 if minutes else 0
    pause_file().write_text(str(until))


def resume():
    pause_file().unlink(missing_ok=True)


def check_achievements(db, cfg, notify=True):
    today = date.today()
    new = achievements.evaluate(db, cfg, today - timedelta(days=8), today)
    for u in new:
        line = f"{u.achievement.emoji} {u.achievement.name}: {u.detail}"
        print(f"[{datetime.now():%H:%M}] Achievement unlocked! {line}", flush=True)
        if notify and cfg.get("notify_achievements", True):
            sensors.notify("Achievement unlocked!", line)
    return new


def maybe_nudge(db, cfg):
    """One gentle nudge near the end of the workday if no win was logged today."""
    if not cfg.get("end_of_day_nudge", True):
        return
    now = datetime.now()
    h, m = (int(x) for x in cfg["workday_end"].split(":"))
    nudge_at = now.replace(hour=h, minute=m, second=0, microsecond=0) - timedelta(minutes=15)
    today = now.date().isoformat()
    if now < nudge_at or now.weekday() >= 5 or db.get_meta("nudged") == today:
        return
    db.set_meta("nudged", today)
    start, end = A.day_range(now.date(), now.date())
    if not db.wins_between(start, end):
        sensors.notify("Brag Book", "What's one thing you moved forward today? "
                       "Run: bragbook win")


def run(db, cfg, verbose=False):
    interval = cfg["sample_seconds"]
    idle_limit = cfg["idle_seconds"]
    print(f"Brag Book is tracking every {interval}s. Data stays in {config.home()}. Ctrl+C to stop.",
          flush=True)
    last_eval = 0.0
    while True:
        started = time.time()
        if not paused():
            win = sensors.active_window()
            idle = sensors.idle_seconds()
            away = idle is not None and idle >= idle_limit
            if win and not away and (win[0] or win[1]):
                app, title = win
                if not is_excluded(app, title, cfg["exclude"]):
                    db.add_sample(started, interval, app, title)
                    if verbose:
                        print(f"{datetime.now():%H:%M:%S}  {app} | {title}", flush=True)
        if started - last_eval >= EVALUATE_EVERY:
            last_eval = started
            try:
                check_achievements(db, cfg)
                maybe_nudge(db, cfg)
            except Exception as e:  # never let a badge bug stop tracking
                print(f"achievement check failed: {e}", flush=True)
        time.sleep(max(1.0, interval - (time.time() - started)))
