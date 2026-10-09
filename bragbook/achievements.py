"""Achievement rules.

Daily and weekly badges can be earned again every day / week. Milestones are earned once.
Some badges reward *sustainable* work (breaks, logging off, quiet weekends) on purpose:
a brag book shouldn't only reward grinding.
"""

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable, Dict, List, Optional

from bragbook import analysis as A


@dataclass
class Achievement:
    id: str
    name: str
    emoji: str
    description: str
    period: str  # "day" | "week" | "milestone"
    check: Callable[..., Optional[str]]
    # Only judge once the day/week is over (for "you didn't do X" badges).
    final_only: bool = False


@dataclass
class DayCtx:
    day: date
    samples: List[A.Sample]
    wins: list
    cfg: dict

    @property
    def deep(self) -> set:
        return set(self.cfg["deep_work_categories"])


@dataclass
class WeekCtx:
    start: date
    days: Dict[date, List[A.Sample]]
    wins: list
    cfg: dict

    @property
    def samples(self) -> List[A.Sample]:
        return [s for d in sorted(self.days) for s in self.days[d]]

    @property
    def deep(self) -> set:
        return set(self.cfg["deep_work_categories"])


@dataclass
class MilestoneCtx:
    total_seconds: float
    deep_seconds: float
    win_count: int


# --- daily ------------------------------------------------------------------

def _deep_dive(c: DayCtx):
    runs = A.focus_runs(c.samples, c.deep)
    best = max(runs, key=lambda r: r.seconds, default=None)
    if best and best.seconds >= 90 * 60:
        return f"{round(best.seconds / 60)} min of unbroken focus on {best.top_category}"


def _flow_state(c: DayCtx):
    secs = sum(s.duration for s in c.samples if s.category in c.deep)
    if secs >= 4 * 3600:
        return f"{A.hours(secs)} of deep work in one day"


def _category_day(category: str, minimum_minutes: int, what: str):
    def check(c: DayCtx):
        secs = sum(s.duration for s in c.samples if s.category == category)
        if secs >= minimum_minutes * 60:
            arts = Counter()
            for s in c.samples:
                if s.category == category and s.artifact:
                    arts[s.artifact] += s.duration
            top = arts.most_common(1)
            on = f" (mostly “{top[0][0]}”)" if top else ""
            return f"{A.hours(secs)} {what}{on}"
    return check


def _plate_spinner(c: DayCtx):
    arts = {s.artifact for s in c.samples if s.artifact}
    if len(arts) >= 6:
        return f"Moved {len(arts)} different pieces of work forward"


def _meeting_marathon(c: DayCtx):
    secs = sum(s.duration for s in c.samples if s.category == "Meetings")
    if secs >= 4 * 3600:
        return f"{A.hours(secs)} in meetings. That's a lot of alignment. Be kind to yourself tonight."


def _recharge(c: DayCtx):
    total = sum(s.duration for s in c.samples)
    if total < 4 * 3600:
        return None
    longest = A.longest_without_break(c.samples, c.cfg["break_minutes"] * 60)
    if longest <= 2 * 3600:
        return f"{A.hours(total)} of work, never more than {A.hours(longest)} without a break"


def _clean_shutdown(c: DayCtx):
    total = sum(s.duration for s in c.samples)
    if total >= 3 * 3600 and A.seconds_after(c.samples, c.cfg["workday_end"]) < 5 * 60:
        return f"Logged off by {c.cfg['workday_end']}"


# --- weekly -----------------------------------------------------------------

def _hat_trick(c: WeekCtx):
    if len(c.wins) >= 3:
        return f"{len(c.wins)} wins logged this week"


def _full_house(c: WeekCtx):
    weekdays = {A.to_date(w["ts"]) for w in c.wins if A.to_date(w["ts"]).weekday() < 5}
    if len(weekdays) >= 5:
        return "A win logged every weekday"


def _range(c: WeekCtx):
    secs = A.category_seconds(c.samples)
    cats = [k for k in c.deep if secs.get(k, 0) >= 3600]
    if len(cats) >= 4:
        return "1h+ in each of: " + ", ".join(sorted(cats))


def _steady_engine(c: WeekCtx):
    n = 0
    for samples in c.days.values():
        runs = A.focus_runs(samples, c.deep)
        if any(r.seconds >= 90 * 60 for r in runs):
            n += 1
    if n >= 3:
        return f"Deep Dives on {n} days this week"


def _weekend_guardian(c: WeekCtx):
    weekend = [c.start + timedelta(days=5), c.start + timedelta(days=6)]
    secs = sum(s.duration for d in weekend for s in c.days.get(d, []))
    weekday_secs = sum(s.duration for d, ss in c.days.items() if d.weekday() < 5 for s in ss)
    if weekday_secs >= 5 * 3600 and secs < 30 * 60:
        return "Protected your weekend"


# --- milestones -------------------------------------------------------------

def _hours_milestone(n: int):
    def check(c: MilestoneCtx):
        if c.deep_seconds >= n * 3600:
            return f"{n} hours of deep work tracked"
    return check


def _wins_milestone(n: int):
    def check(c: MilestoneCtx):
        if c.win_count >= n:
            return f"{n} win{'s' if n > 1 else ''} in the book"
    return check


ACHIEVEMENTS: List[Achievement] = [
    # daily
    Achievement("deep_dive", "Deep Dive", "🌊", "90+ minutes of unbroken focus", "day", _deep_dive),
    Achievement("flow_state", "Flow State", "🔥", "4+ hours of deep work in a day", "day", _flow_state),
    Achievement("deck_builder", "Deck Builder", "🎤", "2+ hours building presentations", "day",
                _category_day("Presentations", 120, "building decks")),
    Achievement("wordsmith", "Wordsmith", "✍️", "2+ hours on strategy docs and writing", "day",
                _category_day("Strategy & Writing", 120, "writing")),
    Achievement("number_cruncher", "Number Cruncher", "📊", "90+ minutes in data and analysis", "day",
                _category_day("Data & Analysis", 90, "in the numbers")),
    Achievement("visionary", "Visionary", "🎨", "90+ minutes designing or mapping", "day",
                _category_day("Design & Visual", 90, "designing")),
    Achievement("plate_spinner", "Plate Spinner", "🎪", "Worked on 6+ different things in a day", "day",
                _plate_spinner),
    Achievement("meeting_marathon", "Meeting Marathoner", "🏃", "Survived 4+ hours of meetings", "day",
                _meeting_marathon),
    Achievement("recharge", "Recharge Respecter", "🔋",
                "4+ hour day with a real break at least every 2 hours", "day", _recharge, final_only=True),
    Achievement("clean_shutdown", "Clean Shutdown", "🌙", "Worked a solid day and logged off on time",
                "day", _clean_shutdown, final_only=True),
    # weekly
    Achievement("hat_trick", "Hat Trick", "🎩", "3+ wins logged in a week", "week", _hat_trick),
    Achievement("full_house", "Full House", "🃏", "A win logged every weekday", "week", _full_house),
    Achievement("range", "Range", "🧭", "1h+ in four different kinds of deep work in a week", "week", _range),
    Achievement("steady_engine", "Steady Engine", "⚙️", "Deep Dives on 3+ days in a week", "week",
                _steady_engine),
    Achievement("weekend_guardian", "Weekend Guardian", "🛡️", "A full work week and a quiet weekend",
                "week", _weekend_guardian, final_only=True),
    # milestones
    Achievement("hours_10", "Getting Started", "🌱", "10 hours of deep work tracked", "milestone",
                _hours_milestone(10)),
    Achievement("hours_50", "In the Groove", "🎶", "50 hours of deep work tracked", "milestone",
                _hours_milestone(50)),
    Achievement("hours_100", "Century", "💯", "100 hours of deep work tracked", "milestone",
                _hours_milestone(100)),
    Achievement("hours_250", "Seasoned Pro", "🏟️", "250 hours of deep work tracked", "milestone",
                _hours_milestone(250)),
    Achievement("hours_500", "Hall of Famer", "🏆", "500 hours of deep work tracked", "milestone",
                _hours_milestone(500)),
    Achievement("wins_1", "First Receipt", "🧾", "Logged your first win", "milestone", _wins_milestone(1)),
    Achievement("wins_10", "Highlight Reel", "🎬", "10 wins logged", "milestone", _wins_milestone(10)),
    Achievement("wins_25", "Portfolio", "🗂️", "25 wins logged", "milestone", _wins_milestone(25)),
    Achievement("wins_50", "Legend", "👑", "50 wins logged", "milestone", _wins_milestone(50)),
]

BY_ID = {a.id: a for a in ACHIEVEMENTS}


@dataclass
class Unlock:
    achievement: Achievement
    period_key: str
    day: str
    detail: str


def evaluate(db, cfg: dict, first: date, last: date, today: Optional[date] = None) -> List[Unlock]:
    """Check every badge for the days/weeks in [first, last]. Returns only *new* unlocks."""
    today = today or date.today()
    last = min(last, today)
    if first > last:
        return []
    week0 = A.week_start(first)
    start_ts, end_ts = A.day_range(week0, last)
    samples = A.load_samples(db, cfg, start_ts, end_ts)
    days = A.by_day(samples)
    wins = db.wins_between(start_ts, end_ts)
    new: List[Unlock] = []

    def record(a: Achievement, period_key: str, day: date, detail: Optional[str]):
        if detail and db.add_unlock(a.id, period_key, day.isoformat(), detail):
            new.append(Unlock(a, period_key, day.isoformat(), detail))

    d = first
    while d <= last:
        ctx = DayCtx(d, days.get(d, []), [w for w in wins if A.to_date(w["ts"]) == d], cfg)
        if ctx.samples or ctx.wins:
            for a in ACHIEVEMENTS:
                if a.period == "day" and not (a.final_only and d >= today):
                    record(a, d.isoformat(), d, a.check(ctx))
        d += timedelta(days=1)

    w = week0
    while w <= last:
        week_end = w + timedelta(days=6)
        wdays = {k: v for k, v in days.items() if w <= k <= week_end}
        wwins = [x for x in wins if w <= A.to_date(x["ts"]) <= week_end]
        ctx = WeekCtx(w, wdays, wwins, cfg)
        iso = w.isocalendar()
        key = f"{iso[0]}-W{iso[1]:02d}"
        for a in ACHIEVEMENTS:
            if a.period == "week" and not (a.final_only and week_end >= today):
                # Weekly badges are filed under the last day of the week (or today, if it's ongoing).
                record(a, key, min(week_end, today), a.check(ctx))
        w += timedelta(days=7)

    deep = set(cfg["deep_work_categories"])
    earned = {u["achievement_id"] for u in db.all_unlocks()}
    first_ts = db.first_sample_ts()
    deep_secs = 0.0
    hour_badges = [a.id for a in ACHIEVEMENTS if a.id.startswith("hours_")]
    if first_ts is not None and not all(b in earned for b in hour_badges):
        deep_secs = sum(s.duration for s in A.load_samples(db, cfg, first_ts, A.day_range(today, today)[1])
                        if s.category in deep)
    mctx = MilestoneCtx(db.total_seconds(), deep_secs, db.win_count())
    for a in ACHIEVEMENTS:
        if a.period == "milestone":
            record(a, "once", today, a.check(mctx))
    return new
