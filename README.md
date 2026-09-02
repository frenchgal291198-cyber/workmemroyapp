# Bowl Report

A tracker of US professional-league stadium and arena capital projects: new builds, major renovations, proposals, and stalled or dead deals across the NFL, MLB, NBA, NHL, MLS, NWSL and WNBA.

The page opens with a dated "what moved" feed, then a filterable register where every project carries cost, public/private split, timeline, what changed versus the earlier plan, open questions, and sources.

## Files

| Path | What it is |
| --- | --- |
| `data/projects.json` | Source of truth. One record per project plus `asOf`, `changeWindowDays`, and a footer note. |
| `src/template.html` | The page (CSS + JS). Data is inlined at build time. |
| `build.js` | Validates the data and writes `index.html`. |
| `index.html` | Built output. Open it directly in a browser or publish it. |
| `CHANGELOG.md` | Human log of what was updated on each refresh. |

## Updating

1. Edit `data/projects.json`. Bump `asOf`.
2. Run `node build.js`. It fails loudly on a missing field, duplicate id, bad stage or bad date.
3. Add a line to `CHANGELOG.md`.

## Record shape

```json
{
  "id": "nfl-browns",
  "league": "NFL",                         // or ["NBA", "NHL"] for shared venues
  "team": "Cleveland Browns",
  "venue": "Huntington Bank Field (Brook Park)",
  "city": "Brook Park", "state": "OH",
  "stage": "construction",                 // construction | approved | proposed | stalled | open | dead
  "type": "New build, enclosed dome",
  "headline": "One-line current state shown in the register row",
  "status": "Two or three sentences of context",
  "thesis": "One line on the experience idea behind the project",
  "scope": ["Concrete physical changes: bowl, premium, concourses, F&B, roof, tech, district"],
  "cost": "$2.4B",
  "funding": "$1.2B private / $600M state / $600M local",
  "target": "2029 season",
  "owner": "Haslam Sports Group",
  "timeline": [{ "date": "2025-06", "text": "State budget approves $600M" }],
  "recent": [{ "date": "2026-08-14", "text": "Dated development (feeds the What moved list)" }],
  "changes": ["Scope, cost, site or funding shifts vs. the earlier plan"],
  "open_questions": ["Unresolved items and who decides them"],
  "next_milestone": { "date": "2026-11", "text": "Council vote on infrastructure bonds" },
  "confidence": "check",                   // optional: flag thin or conflicting sourcing
  "sources": [{ "title": "Outlet", "url": "https://...", "date": "2026-08-14" }]
}
```

`recent` entries inside the change window (default 90 days from `asOf`) surface in the feed at the top of the page.
