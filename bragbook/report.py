"""Build the brag book: wins, achievements, drafted bullets and where your time went."""

import html
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional

from bragbook import achievements, analysis as A

# How each kind of work reads as a bullet: (verb, singular, plural)
PHRASES = {
    "Presentations": ("Built and refined", "deck", "decks"),
    "Strategy & Writing": ("Wrote and shaped", "strategy doc", "strategy docs"),
    "Data & Analysis": ("Dug into the numbers across", "analysis", "analyses"),
    "Design & Visual": ("Designed and mapped", "visual", "visuals"),
    "Planning & Projects": ("Drove planning across", "workstream", "workstreams"),
    "Building & Code": ("Built", "tool", "tools"),
}


@dataclass
class Bullet:
    text: str
    source: str  # "win" | "draft"
    impact: str = ""


@dataclass
class BragData:
    first: date
    last: date
    label: str
    wins: list
    badges: List[dict]
    categories: List[tuple]
    artifacts: Dict[str, List[tuple]]
    bullets: List[Bullet]
    stats: Dict[str, str]
    wellbeing: List[tuple] = field(default_factory=list)


def period(name: str, today: Optional[date] = None):
    today = today or date.today()
    if name == "today":
        return today, today, "Today"
    if name == "week":
        start = A.week_start(today)
        return start, today, f"Week of {md(start)}"
    if name == "month":
        start = today.replace(day=1)
        return start, today, f"{today:%B %Y}"
    if name == "quarter":
        q = (today.month - 1) // 3
        start = date(today.year, q * 3 + 1, 1)
        return start, today, f"Q{q + 1} {today.year}"
    if name == "year":
        return date(today.year, 1, 1), today, f"{today.year}"
    raise ValueError(name)


def _quote_list(names: List[str]) -> str:
    q = [f"“{n}”" for n in names]
    return q[0] if len(q) == 1 else ", ".join(q[:-1]) + " and " + q[-1]


def draft_bullets(samples, artifacts, deep) -> List[Bullet]:
    out: List[Bullet] = []
    secs = A.category_seconds(samples)
    for cat, (verb, one, many) in PHRASES.items():
        if secs.get(cat, 0) < 3600:
            continue
        arts = artifacts.get(cat, [])
        h = A.hours(secs[cat])
        if not arts:
            out.append(Bullet(f"{verb} {many} ({h} of focused work).", "draft"))
        elif len(arts) == 1:
            name, _, days = arts[0]
            out.append(Bullet(f"{verb} “{name}” ({h} over {days} day{'s' if days > 1 else ''}).", "draft"))
        else:
            top = [a[0] for a in arts[:3]]
            out.append(Bullet(f"{verb} {len(arts)} {many} ({h}), including {_quote_list(top)}.", "draft"))
    meetings = [s for s in samples if s.category == "Meetings"]
    if sum(s.duration for s in meetings) >= 3600:
        mdays = len({A.to_date(s.ts) for s in meetings})
        out.append(Bullet(f"Showed up for {A.hours(sum(s.duration for s in meetings))} of meetings and "
                          f"working sessions across {mdays} day{'s' if mdays > 1 else ''}.", "draft"))
    return out


def build(db, cfg: dict, first: date, last: date, label: str) -> BragData:
    achievements.evaluate(db, cfg, first, last)
    start, end = A.day_range(first, last)
    samples = A.load_samples(db, cfg, start, end)
    deep = set(cfg["deep_work_categories"])
    days = A.by_day(samples)

    wins = [dict(w) for w in db.wins_between(start, end)]
    for w in wins:
        w["date"] = A.to_date(w["ts"])

    # Badges, grouped: name, how many times, latest detail.
    grouped: Dict[str, dict] = {}
    for u in db.unlocks_between(first.isoformat(), last.isoformat()):
        a = achievements.BY_ID.get(u["achievement_id"])
        if not a:
            continue
        g = grouped.setdefault(a.id, {"a": a, "count": 0, "detail": "", "day": ""})
        g["count"] += 1
        if u["day"] >= g["day"]:
            g["day"], g["detail"] = u["day"], u["detail"]
    order = {a.id: i for i, a in enumerate(achievements.ACHIEVEMENTS)}
    badges = sorted(grouped.values(), key=lambda g: order[g["a"].id])

    cat_secs = A.category_seconds(samples)
    categories = sorted(((c, s) for c, s in cat_secs.items() if s >= 60), key=lambda x: -x[1])

    artifacts: Dict[str, List[tuple]] = {}
    for cat, arts in A.artifact_stats(samples).items():
        ranked = sorted(arts.items(), key=lambda kv: -kv[1]["seconds"])
        artifacts[cat] = [(name, v["seconds"], len(v["days"])) for name, v in ranked if v["seconds"] >= 10 * 60]

    bullets = [Bullet(w["text"], "win", w["impact"]) for w in wins]
    bullets += draft_bullets(samples, {c: [(n, s, d) for n, s, d in v] for c, v in artifacts.items()}, deep)

    runs = A.focus_runs(samples, deep)
    best = max(runs, key=lambda r: r.seconds, default=None)
    deep_secs = sum(s for c, s in cat_secs.items() if c in deep)
    stats = {
        "Wins logged": str(len(wins)),
        "Badges earned": str(sum(g["count"] for g in badges)),
        "Deep work": A.hours(deep_secs),
        "Longest focus": A.hours(best.seconds) if best else "–",
    }

    wellbeing = []
    if days:
        total = sum(cat_secs.values())
        weekdays = [d for d in days if d.weekday() < 5]
        late = [d for d, ss in days.items() if A.seconds_after(ss, cfg["workday_end"]) >= 15 * 60]
        weekend = sum(s.duration for d, ss in days.items() if d.weekday() >= 5 for s in ss)
        stretch = [A.longest_without_break(ss, cfg["break_minutes"] * 60) for ss in days.values()]
        wellbeing = [
            ("Average tracked day", A.hours(total / len(days))),
            (f"Days you worked past {cfg['workday_end']}", f"{len(late)} of {len(days)}"),
            ("Weekend time", A.hours(weekend) if weekend else "None. Nice."),
            ("Typical longest stretch without a break", A.hours(sorted(stretch)[len(stretch) // 2])),
        ]
        if not weekdays:
            wellbeing = wellbeing[:1] + wellbeing[2:]

    return BragData(first, last, label, wins, badges, categories, artifacts, bullets, stats, wellbeing)


# --- Markdown ---------------------------------------------------------------

def to_markdown(d: BragData) -> str:
    lines = [f"# Brag Book: {d.label}", f"_{span(d.first, d.last)}_", ""]
    lines += [" · ".join(f"**{v}** {k.lower()}" for k, v in d.stats.items()), ""]
    lines += ["## Wins", ""]
    if d.wins:
        for w in d.wins:
            impact = f" → {w['impact']}" if w["impact"] else ""
            tags = f" `{w['tags']}`" if w["tags"] else ""
            lines.append(f"- **{md(w['date'])}:** {w['text']}{impact}{tags}")
    else:
        lines.append("_No wins logged yet. Run `bragbook win` and add one._")
    drafts = [b for b in d.bullets if b.source == "draft"]
    if drafts:
        lines += ["", "## Drafted from your activity", "_Add the result to each: what changed, for whom, by how much?_", ""]
        lines += [f"- {b.text}" for b in drafts]
    if d.badges:
        lines += ["", "## Achievements", ""]
        for g in d.badges:
            times = f" ×{g['count']}" if g["count"] > 1 else ""
            lines.append(f"- {g['a'].emoji} **{g['a'].name}**{times}: {g['detail']}")
    if d.categories:
        lines += ["", "## Where the time went", ""]
        lines += [f"- {c}: {A.hours(s)}" for c, s in d.categories]
    if d.artifacts:
        lines += ["", "## What you worked on", ""]
        for cat, arts in d.artifacts.items():
            if arts:
                lines.append(f"**{cat}:** " + "; ".join(f"{n} ({A.hours(s)})" for n, s, _ in arts[:6]))
                lines.append("")
    if d.wellbeing:
        lines += ["", "## Sustainability check", ""]
        lines += [f"- {k}: {v}" for k, v in d.wellbeing]
    return "\n".join(lines).rstrip() + "\n"


# --- HTML -------------------------------------------------------------------

CSS = """
:root{
  --bg:#f6f4ef;--surface:#fffdf9;--surface-2:#f0ede5;--border:#e3ded2;
  --text:#1b1a17;--text-2:#55524b;--muted:#8a867c;
  --accent:#c2410c;--accent-soft:#fbe7dc;--bar:#2a78d6;--win:#0f766e;--win-soft:#dcf2ee;
  color-scheme:light;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --bg:#141413;--surface:#1c1c1a;--surface-2:#252522;--border:#33322e;
    --text:#f5f3ee;--text-2:#c3c2b7;--muted:#8f8d84;
    --accent:#fb923c;--accent-soft:#3a2417;--bar:#3987e5;--win:#5eead4;--win-soft:#123430;
    color-scheme:dark;
  }
}
:root[data-theme="dark"]{
  --bg:#141413;--surface:#1c1c1a;--surface-2:#252522;--border:#33322e;
  --text:#f5f3ee;--text-2:#c3c2b7;--muted:#8f8d84;
  --accent:#fb923c;--accent-soft:#3a2417;--bar:#3987e5;--win:#5eead4;--win-soft:#123430;
  color-scheme:dark;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);
  font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:920px;margin:0 auto;padding:40px 16px 64px}
header{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;margin-bottom:28px}
.eyebrow{color:var(--accent);font-weight:600;letter-spacing:.08em;text-transform:uppercase;font-size:12px}
h1{font:600 40px/1.1 ui-serif,Georgia,"Times New Roman",serif;margin:4px 0 6px;letter-spacing:-.01em}
.range{color:var(--text-2)}
h2{font:600 22px/1.2 ui-serif,Georgia,serif;margin:0 0 4px}
.sub{color:var(--muted);font-size:13px;margin:0 0 16px}
section{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:22px 22px 20px;margin-top:18px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.stat{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:16px}
.stat b{display:block;font:600 28px/1.1 ui-serif,Georgia,serif}
.stat span{color:var(--text-2);font-size:13px}
ul.wins{list-style:none;margin:0;padding:0}
ul.wins li{display:grid;grid-template-columns:64px 1fr;gap:12px;padding:12px 0;border-top:1px solid var(--border)}
ul.wins li:first-child{border-top:0;padding-top:4px}
.date{color:var(--muted);font-size:13px;padding-top:2px;font-variant-numeric:tabular-nums}
.impact{display:block;width:fit-content;margin-top:4px;background:var(--win-soft);color:var(--win);border-radius:6px;padding:1px 8px;font-size:13px}
.tag{display:inline-block;margin:4px 6px 0 0;color:var(--text-2);background:var(--surface-2);border-radius:999px;padding:0 9px;font-size:12px}
ul.drafts{margin:0;padding-left:20px}
ul.drafts li{margin:0 0 10px}
.hint{display:block;color:var(--muted);font-size:13px}
.badges{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px}
.badge{border:1px solid var(--border);border-radius:12px;padding:14px;background:var(--surface-2)}
.badge .e{font-size:28px;line-height:1}
.badge b{display:block;margin-top:8px}
.badge .n{color:var(--accent);font-weight:600;font-size:13px;margin-left:4px}
.badge p{margin:4px 0 0;color:var(--text-2);font-size:13px}
.bars{display:grid;grid-template-columns:minmax(120px,190px) 1fr;gap:8px 14px;align-items:center}
.bars .lbl{color:var(--text-2);font-size:14px}
.track{display:flex;align-items:center;gap:8px;min-width:0}
.bar{height:14px;background:var(--bar);border-radius:0 4px 4px 0;min-width:2px}
.val{color:var(--text);font-size:13px;font-variant-numeric:tabular-nums;white-space:nowrap}
.cat{margin-top:14px}
.cat h3{font-size:14px;margin:0 0 6px;color:var(--text-2);font-weight:600}
table{width:100%;border-collapse:collapse;font-size:14px}
td{padding:6px 0;border-top:1px solid var(--border)}
td.num{text-align:right;color:var(--text-2);font-variant-numeric:tabular-nums;white-space:nowrap;padding-left:12px}
dl.well{display:grid;grid-template-columns:1fr auto;gap:8px 16px;margin:0}
dl.well dt{color:var(--text-2)} dl.well dd{margin:0;font-weight:600;text-align:right}
.empty{color:var(--muted)}
button.copy{font:inherit;font-size:13px;border:1px solid var(--border);background:var(--surface-2);color:var(--text);
  border-radius:8px;padding:6px 12px;cursor:pointer}
button.copy:hover{border-color:var(--accent)}
.head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
footer{color:var(--muted);font-size:12px;margin-top:28px;text-align:center}
@media (max-width:640px){
  h1{font-size:32px}
  .stats{grid-template-columns:repeat(2,1fr)}
  .bars{grid-template-columns:1fr}
  .bars .lbl{margin-top:6px}
  section{padding:18px 16px}
}
/* live dashboard */
.status{display:flex;align-items:center;gap:8px;flex-wrap:wrap;color:var(--text-2);font-size:13px;margin:-12px 0 16px}
.dot{width:8px;height:8px;border-radius:50%;background:var(--muted);flex:none}
.dot.on{background:#16a34a}.dot.off{background:#dc2626}.dot.paused{background:#d97706}
.status form{display:inline;margin:0}
.linkbtn{font:inherit;font-size:13px;background:none;border:0;color:var(--accent);cursor:pointer;padding:0;text-decoration:underline}
nav.tabs{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 16px}
nav.tabs a{color:var(--text-2);text-decoration:none;border:1px solid var(--border);border-radius:999px;padding:5px 14px;font-size:14px;background:var(--surface)}
nav.tabs a.on{background:var(--text);color:var(--bg);border-color:var(--text)}
form.winform{background:var(--surface);border:2px solid var(--accent);border-radius:14px;padding:16px;margin:0 0 18px;display:grid;gap:10px}
form.winform label{font-weight:600}
form.winform .row{display:grid;grid-template-columns:1fr 1fr auto;gap:10px}
form.winform input{font:inherit;width:100%;border:1px solid var(--border);border-radius:8px;padding:9px 11px;background:var(--bg);color:var(--text)}
form.winform input:focus{outline:2px solid var(--accent);outline-offset:1px}
form.winform button{font:inherit;font-weight:600;border:0;border-radius:8px;padding:9px 18px;background:var(--accent);color:#fff;cursor:pointer}
.flash{background:var(--win-soft);color:var(--win);border-radius:10px;padding:10px 14px;margin:0 0 16px;font-weight:600}
@media (max-width:640px){form.winform .row{grid-template-columns:1fr}}
@media print{body{background:#fff}section,.stat{break-inside:avoid}button,nav.tabs,form.winform,.status{display:none}}
"""


def _e(s) -> str:
    return html.escape(str(s))


def _times(n: int) -> str:
    return f'<span class="n">×{n}</span>' if n > 1 else ""


def md(d: date) -> str:
    """'Oct 9' (strftime's %-d doesn't work on Windows)."""
    return f"{d:%b} {d.day}"


def mdy(d: date) -> str:
    return f"{md(d)}, {d.year}"


def span(first: date, last: date) -> str:
    return mdy(first) if first == last else f"{mdy(first)} – {mdy(last)}"


def to_html(d: BragData, top_html: str = "") -> str:
    """The brag book page. `top_html` lets the live dashboard add its controls above the stats."""
    text = json.dumps(to_markdown(d)).replace("<", "\\u003c")
    stats = "".join(f'<div class="stat"><b>{_e(v)}</b><span>{_e(k)}</span></div>' for k, v in d.stats.items())

    if d.wins:
        items = []
        for w in d.wins:
            impact = f'<div class="impact">→ {_e(w["impact"])}</div>' if w["impact"] else ""
            tags = "".join(f'<span class="tag">{_e(t.strip())}</span>'
                           for t in w["tags"].split(",") if t.strip())
            items.append(f'<li><span class="date">{md(w["date"])}</span>'
                         f'<div>{_e(w["text"])}{impact}{"<div>" + tags + "</div>" if tags else ""}</div></li>')
        wins = f'<ul class="wins">{"".join(items)}</ul>'
    else:
        wins = '<p class="empty">No wins logged in this period yet. Run <code>bragbook win</code> to add one.</p>'

    drafts = [b for b in d.bullets if b.source == "draft"]
    drafts_html = ""
    if drafts:
        lis = "".join(f'<li>{_e(b.text)}<span class="hint">→ Add the result: what changed, for whom, by how much?</span></li>'
                      for b in drafts)
        drafts_html = (f'<section><h2>Drafted from your activity</h2>'
                       f'<p class="sub">Starting points for your review. Your activity shows the effort; you add the outcome.</p>'
                       f'<ul class="drafts">{lis}</ul></section>')

    if d.badges:
        cards = "".join(
            f'<div class="badge" title="{_e(g["a"].description)}"><div class="e">{g["a"].emoji}</div>'
            f'<b>{_e(g["a"].name)}{_times(g["count"])}</b>'
            f'<p>{_e(g["detail"])}</p></div>'
            for g in d.badges)
        badges = f'<div class="badges">{cards}</div>'
    else:
        badges = '<p class="empty">Keep the tracker running and badges will start showing up.</p>'

    time_html = ""
    if d.categories:
        top = d.categories[0][1]
        rows = "".join(
            f'<div class="lbl">{_e(c)}</div><div class="track" title="{_e(c)}: {_e(A.hours(s))}">'
            f'<div class="bar" style="width:{max(1, s / top * 85):.1f}%"></div><span class="val">{_e(A.hours(s))}</span></div>'
            for c, s in d.categories)
        tables = ""
        for cat, arts in d.artifacts.items():
            if not arts:
                continue
            trs = "".join(f'<tr><td>{_e(n)}</td><td class="num">{_e(A.hours(s))} · {dd} day{"s" if dd > 1 else ""}</td></tr>'
                          for n, s, dd in arts[:6])
            tables += f'<div class="cat"><h3>{_e(cat)}</h3><table>{trs}</table></div>'
        time_html = (f'<section><h2>Where the time went</h2><p class="sub">Active time only. Idle and away time is not counted.</p>'
                     f'<div class="bars">{rows}</div></section>')
        if tables:
            time_html += (f'<section><h2>What you worked on</h2>'
                          f'<p class="sub">Pulled from your window titles. These are the receipts.</p>{tables}</section>')

    well = ""
    if d.wellbeing:
        dl = "".join(f"<dt>{_e(k)}</dt><dd>{_e(v)}</dd>" for k, v in d.wellbeing)
        well = (f'<section><h2>Sustainability check</h2>'
                f'<p class="sub">High output is only a win if you can keep it up.</p><dl class="well">{dl}</dl></section>')

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Brag Book</title><style>{CSS}</style></head>
<body><div class="wrap">
<header><div><div class="eyebrow">Brag Book</div><h1>{_e(d.label)}</h1>
<div class="range">{span(d.first, d.last)}</div></div>
<button class="copy" id="copy">Copy as text</button></header>
{top_html}
<div class="stats">{stats}</div>
<section><div class="head"><div><h2>Wins</h2><p class="sub">The things you'd want your boss to remember.</p></div></div>{wins}</section>
{drafts_html}
<section><h2>Achievements</h2><p class="sub">Earned from how you actually worked.</p>{badges}</section>
{time_html}
{well}
<footer>Generated {mdy(date.today())} at {datetime.now():%H:%M} · All data stays on your computer.</footer>
</div>
<script>
const md = {text};
document.getElementById('copy').addEventListener('click', async (e) => {{
  try {{ await navigator.clipboard.writeText(md); e.target.textContent = 'Copied'; }}
  catch (_) {{ e.target.textContent = 'Copy failed'; }}
  setTimeout(() => e.target.textContent = 'Copy as text', 1600);
}});
</script>
</body></html>
"""
