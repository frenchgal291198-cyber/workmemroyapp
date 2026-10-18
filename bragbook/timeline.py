"""A Dayflow-style timeline of your day: activity cards, a day strip and distraction highlights.

Built from the window titles the tracker already records. No screen recording, nothing leaves your computer.
"""

import html
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import List, Optional

from bragbook import analysis as A, report
from bragbook.categorize import extract_artifact

SAME_SESSION_GAP = 5 * 60   # resume the same kind of work within 5 min = same session
DISTRACTION_MAX = 3 * 60    # a detour shorter than this is a distraction, not a new session
MIN_SESSION = 2 * 60        # anything shorter gets folded into its neighbour

# Category colors: fixed order, validated categorical palette (light, dark). Browsing/Other stay neutral.
COLORS = {
    "Presentations": ("#2a78d6", "#3987e5"),
    "Strategy & Writing": ("#eb6834", "#d95926"),
    "Data & Analysis": ("#1baf7a", "#199e70"),
    "Design & Visual": ("#eda100", "#c98500"),
    "Planning & Projects": ("#e87ba4", "#d55181"),
    "Building & Code": ("#008300", "#008300"),
    "Meetings": ("#4a3aa7", "#9085e9"),
    "Communication": ("#e34948", "#e66767"),
    "Research & Browsing": ("#a8a69e", "#6b6a64"),
    "Other": ("#c9c6bd", "#4a4945"),
}
SLUG = {c: f"c{i}" for i, c in enumerate(COLORS)}


@dataclass
class Session:
    category: str
    start: float
    end: float
    seconds: float = 0.0
    things: Counter = field(default_factory=Counter)
    apps: Counter = field(default_factory=Counter)
    distractions: Counter = field(default_factory=Counter)  # app -> seconds
    pulls: int = 0  # how many times you got pulled away

    @property
    def distraction_seconds(self) -> float:
        return sum(self.distractions.values())


def _label(s: A.Sample) -> Optional[str]:
    if s.category == "Communication":
        return None  # don't put email subjects / DMs on your timeline
    return s.artifact or extract_artifact(s.app, s.title, s.category)


def _segments(samples: List[A.Sample]) -> List[Session]:
    """Runs of back-to-back samples in the same category."""
    segs: List[Session] = []
    for s in sorted(samples, key=lambda x: x.ts):
        cur = segs[-1] if segs else None
        if cur and cur.category == s.category and s.ts - cur.end <= A.MAKER_GAP:
            cur.end = s.end
        else:
            cur = Session(s.category, s.ts, s.end)
            segs.append(cur)
        cur.seconds += s.duration
        cur.apps[s.app] += s.duration
        label = _label(s)
        if label:
            cur.things[label] += s.duration
    return segs


def _absorb(into: Session, other: Session, as_distraction: bool):
    into.end = max(into.end, other.end)
    into.start = min(into.start, other.start)
    if as_distraction:
        for app, secs in other.apps.items():
            into.distractions[app] += secs
        into.pulls += 1
    else:
        into.seconds += other.seconds
        into.things.update(other.things)
        into.apps.update(other.apps)
        into.distractions.update(other.distractions)
        into.pulls += other.pulls


def sessions(samples: List[A.Sample]) -> List[Session]:
    segs = _segments(samples)
    out: List[Session] = []
    i = 0
    while i < len(segs):
        seg = segs[i]
        cur = out[-1] if out else None
        nxt = segs[i + 1] if i + 1 < len(segs) else None
        # Same work again soon after: continue the session.
        if cur and seg.category == cur.category and seg.start - cur.end <= SAME_SESSION_GAP:
            _absorb(cur, seg, as_distraction=False)
        # A quick detour you came straight back from: a distraction inside the session.
        elif (cur and nxt and seg.seconds < DISTRACTION_MAX and nxt.category == cur.category
              and nxt.start - cur.end <= SAME_SESSION_GAP):
            _absorb(cur, seg, as_distraction=True)
            _absorb(cur, nxt, as_distraction=False)
            i += 1
        else:
            out.append(seg)
        i += 1
    # Fold crumbs (< 2 min) into the session before them, if it's adjacent.
    tidy: List[Session] = []
    for s in out:
        if tidy and s.seconds < MIN_SESSION and s.start - tidy[-1].end <= SAME_SESSION_GAP:
            _absorb(tidy[-1], s, as_distraction=True)
        else:
            tidy.append(s)
    return [s for s in tidy if s.seconds >= 60]


def _quote(names):
    return report._quote_list(list(names))


def title(s: Session) -> str:
    names = [n for n, _ in s.things.most_common()]
    if s.category == "Communication":
        apps = [a for a, _ in s.apps.most_common(2)]
        return "Catching up on " + " and ".join(apps)
    if s.category == "Meetings":
        name = names[0] if names else ""
        if not name or name.lower().startswith(("meet", "zoom")):  # "Meet - abc-defg-hij", "Zoom Meeting"
            app = s.apps.most_common(1)[0][0].lower() if s.apps else ""
            return "Zoom call" if "zoom" in app or "zoom" in name.lower() else "Video call"
        return name
    if not names:
        return s.category
    return names[0] if len(names) == 1 else f"{names[0]} + {len(names) - 1} more"


VERBS = {
    "Presentations": "Worked on", "Strategy & Writing": "Wrote", "Data & Analysis": "Analysed",
    "Design & Visual": "Designed", "Planning & Projects": "Planned in", "Building & Code": "Built",
    "Research & Browsing": "Read up on", "Meetings": "In", "Other": "Used",
}


def summary(s: Session) -> str:
    names = [n for n, _ in s.things.most_common(3)]
    if s.category == "Communication":
        text = f"Messages and email for {A.hours(s.seconds)}."
    elif s.category == "Meetings":
        text = f"{A.hours(s.seconds)} in {'calls' if s.seconds > 3600 else 'a call'}."
    elif names:
        text = f"{VERBS.get(s.category, 'Worked on')} {_quote(names)}."
    else:
        apps = [a for a, _ in s.apps.most_common(2)]
        text = f"{VERBS.get(s.category, 'Used')} {' and '.join(apps)}."
    if s.distractions:
        top = s.distractions.most_common(1)[0][0]
        text += f" Pulled away {s.pulls}× ({A.hours(s.distraction_seconds)}, mostly {top})."
    return text


def _clock(ts: float) -> str:
    t = datetime.fromtimestamp(ts)
    return f"{t.hour % 12 or 12}:{t.minute:02d} {'am' if t.hour < 12 else 'pm'}"


# --- terminal ---------------------------------------------------------------

def to_text(sess: List[Session]) -> str:
    if not sess:
        return "Nothing tracked for this day."
    lines = []
    for s in sess:
        lines.append(f"{_clock(s.start):>8} – {_clock(s.end):<8} {s.category:<20} {title(s)}")
        lines.append(f"{'':>20} {A.hours(s.seconds)} · {summary(s)}")
    return "\n".join(lines)


# --- HTML -------------------------------------------------------------------

def _css() -> str:
    light = "".join(f"--{SLUG[c]}:{v[0]};" for c, v in COLORS.items())
    dark = "".join(f"--{SLUG[c]}:{v[1]};" for c, v in COLORS.items())
    return f"""
:root{{{light}}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{{dark}}}}}
:root[data-theme="dark"]{{{dark}}}
.daynav{{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0 0 14px}}
.daynav a{{color:var(--text-2);text-decoration:none;border:1px solid var(--border);border-radius:999px;padding:5px 14px;font-size:14px;background:var(--surface)}}
.daynav a.dis{{visibility:hidden}}
.daynav b{{font:600 22px/1.2 ui-serif,Georgia,serif}}
.headline{{color:var(--text-2);margin:0 0 14px}}
.strip{{position:relative;height:30px;background:var(--surface-2);border-radius:8px;overflow:hidden}}
.strip span{{position:absolute;top:0;bottom:0;border-right:2px solid var(--surface-2)}}
.hours{{position:relative;height:18px;margin-top:4px;font-size:11px;color:var(--muted)}}
.hours span{{position:absolute;transform:translateX(-50%);white-space:nowrap}}
.legend{{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:10px;font-size:12px;color:var(--text-2)}}
.legend i{{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px;vertical-align:-1px}}
.cards{{display:grid;gap:10px}}
.card{{display:grid;grid-template-columns:96px 1fr;gap:14px;background:var(--surface);border:1px solid var(--border);
  border-left:6px solid var(--cat);border-radius:12px;padding:14px 16px}}
.card .when{{color:var(--text-2);font-size:13px;font-variant-numeric:tabular-nums;line-height:1.4}}
.card .when b{{display:block;color:var(--text);font-size:15px}}
.card h3{{margin:0;font-size:16px;font-weight:600;overflow-wrap:anywhere}}
.card .cat{{display:inline-block;margin:2px 0 6px;font-size:12px;color:var(--text-2)}}
.card .cat i{{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--cat);margin-right:6px}}
.card p{{margin:0;color:var(--text-2);font-size:14px}}
.card .distract{{color:var(--accent)}}
.gap{{color:var(--muted);font-size:13px;padding:2px 0 2px 112px}}
.timeline-empty{{background:var(--surface);border:1px dashed var(--border);border-radius:14px;padding:28px;text-align:center;color:var(--text-2)}}
@media (max-width:640px){{.card{{grid-template-columns:1fr;gap:6px}}.gap{{padding-left:0}}.hours span:nth-child(even){{display:none}}}}
"""


def day_html(db, cfg, day: date, today: Optional[date] = None) -> str:
    today = today or date.today()
    start, end = A.day_range(day, day)
    samples = A.load_samples(db, cfg, start, end)
    sess = sessions(samples)
    e = html.escape

    prev_d, next_d = day - timedelta(days=1), day + timedelta(days=1)
    label = "Today" if day == today else ("Yesterday" if day == today - timedelta(days=1)
                                          else f"{day:%A}, {report.md(day)}")
    nav = (f'<div class="daynav"><a href="/?d={prev_d}">← {e(report.md(prev_d))}</a><b>{e(label)}</b>'
           f'<a href="/?d={next_d}" class="{"dis" if day >= today else ""}">{e(report.md(next_d))} →</a></div>')

    if not sess:
        msg = ("Nothing tracked yet today. Keep the tracker running and your day will fill in here."
               if day == today else "Nothing was tracked on this day.")
        return nav + f'<div class="timeline-empty">{e(msg)}</div>'

    deep = set(cfg["deep_work_categories"])
    total = sum(s.seconds for s in sess)
    deep_secs = sum(s.seconds for s in sess if s.category in deep)
    runs = A.focus_runs(samples, deep)
    best = max((r.seconds for r in runs), default=0)
    pulls = Counter()
    for s in sess:
        pulls.update(s.distractions)
    n_pulls = sum(s.pulls for s in sess)
    head = [f"<b>{A.hours(total)}</b> tracked", f"<b>{A.hours(deep_secs)}</b> deep work"]
    if best:
        head.append(f"longest focus <b>{A.hours(best)}</b>")
    if n_pulls:
        head.append(f"<b>{n_pulls}</b> distraction{'s' if n_pulls > 1 else ''} (mostly {e(pulls.most_common(1)[0][0])})")

    # Day strip: whole hours from first to last activity.
    h0 = datetime.fromtimestamp(sess[0].start).replace(minute=0, second=0, microsecond=0)
    h1 = datetime.fromtimestamp(sess[-1].end).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    lo, span = h0.timestamp(), max(h1.timestamp() - h0.timestamp(), 3600)
    blocks = "".join(
        f'<span style="left:{(s.start - lo) / span * 100:.2f}%;width:{max((s.end - s.start) / span * 100, 0.4):.2f}%;'
        f'background:var(--{SLUG.get(s.category, "c9")})" title="{e(_clock(s.start))}–{e(_clock(s.end))} · '
        f'{e(s.category)} · {e(title(s))}"></span>' for s in sess)
    n_hours = int(span // 3600)
    step = 1 if n_hours <= 12 else 2
    ticks = "".join(f'<span style="left:{h / n_hours * 100:.2f}%">{e(_clock(lo + h * 3600).replace(":00", ""))}</span>'
                    for h in range(0, n_hours + 1, step))
    used = [c for c in COLORS if any(s.category == c for s in sess)]
    legend = "".join(f'<span><i style="background:var(--{SLUG[c]})"></i>{e(c)}</span>' for c in used)

    cards = []
    prev_end = None
    for s in sess:
        if prev_end and s.start - prev_end >= cfg["break_minutes"] * 60:
            cards.append(f'<div class="gap">☕ Break · {e(A.hours(s.start - prev_end))}</div>')
        summ = e(summary(s))
        if s.distractions:
            cut = summ.find(" Pulled away")
            summ = summ[:cut] + f'<span class="distract">{summ[cut:]}</span>'
        cards.append(
            f'<div class="card" style="--cat:var(--{SLUG.get(s.category, "c9")})">'
            f'<div class="when"><b>{e(_clock(s.start))}</b>to {e(_clock(s.end))}<br>{e(A.hours(s.seconds))}</div>'
            f'<div><h3>{e(title(s))}</h3><span class="cat"><i></i>{e(s.category)}</span><p>{summ}</p></div></div>')
        prev_end = s.end

    return (nav + f'<p class="headline">{" · ".join(head)}</p>'
            f'<section style="margin-top:0"><div class="strip">{blocks}</div><div class="hours">{ticks}</div>'
            f'<div class="legend">{legend}</div></section>'
            f'<div class="cards" style="margin-top:18px">{"".join(cards)}</div>')


def page(db, cfg, day: date, top_html: str = "") -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Brag Book</title><style>{report.CSS}{_css()}</style></head>
<body><div class="wrap">
<header><div><div class="eyebrow">Brag Book</div><h1>Your day</h1></div></header>
{top_html}
{day_html(db, cfg, day)}
<footer>Built from your window titles · All data stays on your computer.</footer>
</div></body></html>
"""
