"""Shape raw samples into days, focus runs, breaks and time-per-thing."""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time as dtime, timedelta
from typing import Dict, List, Optional, Tuple

from bragbook.categorize import categorize, extract_artifact

MAKER_GAP = 120  # seconds of silence that still counts as "the same stretch"


@dataclass
class Sample:
    ts: float
    duration: float
    app: str
    title: str
    category: str
    artifact: Optional[str]

    @property
    def end(self) -> float:
        return self.ts + self.duration


@dataclass
class FocusRun:
    start: float
    end: float
    seconds: float
    categories: Counter = field(default_factory=Counter)

    @property
    def top_category(self) -> str:
        return self.categories.most_common(1)[0][0] if self.categories else "Other"


def day_start(d: date) -> float:
    return datetime.combine(d, dtime.min).timestamp()


def day_range(first: date, last: date) -> Tuple[float, float]:
    return day_start(first), day_start(last + timedelta(days=1))


def to_date(ts: float) -> date:
    return datetime.fromtimestamp(ts).date()


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def load_samples(db, cfg: dict, start: float, end: float) -> List[Sample]:
    cats = cfg["categories"]
    deep = set(cfg["deep_work_categories"])
    out = []
    for row in db.samples_between(start, end):
        cat = categorize(row["app"], row["title"], cats)
        art = extract_artifact(row["app"], row["title"], cat) if cat in deep else None
        out.append(Sample(row["ts"], row["duration"], row["app"], row["title"], cat, art))
    return out


def by_day(samples: List[Sample]) -> Dict[date, List[Sample]]:
    days: Dict[date, List[Sample]] = defaultdict(list)
    for s in samples:
        days[to_date(s.ts)].append(s)
    return dict(days)


def category_seconds(samples: List[Sample]) -> Counter:
    c: Counter = Counter()
    for s in samples:
        c[s.category] += s.duration
    return c


def artifact_stats(samples: List[Sample]) -> Dict[str, Dict[str, dict]]:
    """{category: {artifact: {"seconds": n, "days": {dates}}}}"""
    out: Dict[str, Dict[str, dict]] = defaultdict(dict)
    for s in samples:
        if not s.artifact:
            continue
        entry = out[s.category].setdefault(s.artifact, {"seconds": 0.0, "days": set()})
        entry["seconds"] += s.duration
        entry["days"].add(to_date(s.ts))
    return dict(out)


def focus_runs(samples: List[Sample], deep: set, max_interrupt: float = 120,
               max_gap: float = MAKER_GAP) -> List[FocusRun]:
    """Stretches of deep work. A quick Slack check (< 2 min) doesn't break the run."""
    runs: List[FocusRun] = []
    cur: Optional[FocusRun] = None
    interrupt = 0.0
    last_end = 0.0

    def close():
        nonlocal cur
        if cur and cur.seconds > 0:
            runs.append(cur)
        cur = None

    for s in sorted(samples, key=lambda x: x.ts):
        if cur and s.ts - last_end > max_gap:
            close()
        if s.category in deep:
            if cur is None:
                cur = FocusRun(start=s.ts, end=s.end, seconds=0.0)
            cur.seconds += s.duration
            cur.categories[s.category] += s.duration
            cur.end = s.end
            interrupt = 0.0
        elif cur is not None:
            interrupt += s.duration
            if interrupt > max_interrupt:
                close()
        last_end = s.end
    close()
    return runs


def longest_without_break(samples: List[Sample], break_seconds: float) -> float:
    """Longest stretch of activity with no gap of at least `break_seconds`."""
    best = 0.0
    start = None
    last_end = None
    for s in sorted(samples, key=lambda x: x.ts):
        if start is None or s.ts - last_end >= break_seconds:
            start = s.ts
        last_end = s.end
        best = max(best, last_end - start)
    return best


def seconds_after(samples: List[Sample], hhmm: str) -> float:
    h, m = (int(x) for x in hhmm.split(":"))
    total = 0.0
    for s in samples:
        dt = datetime.fromtimestamp(s.ts)
        if (dt.hour, dt.minute) >= (h, m):
            total += s.duration
    return total


def hours(seconds: float) -> str:
    h = seconds / 3600
    if h < 1:
        return f"{round(seconds / 60)} min"
    return f"{h:.1f}h"
