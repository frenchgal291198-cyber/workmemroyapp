# Brag Book 🧾

Brag Book runs quietly on your computer and notes what you're working on. It turns that into **achievements** and builds a **brag book** you can drop straight into a performance review, promo case or 1:1.

You don't have to remember to write things down. The tracker keeps the receipts, and you add the "so what" whenever you have 10 seconds.

- **Automatic:** every 15 seconds it records the active app and window title, so it knows "2.5h on *Premium Seating Activation - Sponsor Pitch.pptx*". Idle time doesn't count.
- **Achievements:** Deep Dive, Deck Builder, Number Cruncher, Hat Trick, Century and more. You get a desktop notification each time you earn one.
- **Burnout-aware:** some badges reward *sustainable* work, like **Recharge Respecter** (breaks every 2h), **Clean Shutdown** (logged off on time) and **Weekend Guardian**. Every report ends with a sustainability check.
- **Private:** everything stays in `~/.bragbook` on your machine. Password managers, banking and private windows are never recorded. You can also pause tracking or delete recent activity.

## Get started (3 steps)

**Mac / Linux:** open Terminal, paste this and press Enter:

```bash
curl -fsSL https://raw.githubusercontent.com/frenchgal291198-cyber/workmemroyapp/claude/activity-brag-book-tool-9ekn2h/install.sh | bash
```

Then **open a new Terminal window** and run:

```bash
bragbook check               # confirms it can see your windows
bragbook autostart install   # runs in the background from now on, at every login
```

If the installer says you need Python, run `xcode-select --install`, click **Install** in the pop-up, then paste the installer line again.

**Windows, or if you prefer pip:** `pip install git+https://github.com/frenchgal291198-cyber/workmemroyapp.git@claude/activity-brag-book-tool-9ekn2h` (needs Python 3.9+).

That's it. **Now open http://localhost:8642 and bookmark it.** That's your page (see below).

To see what a report looks like before you have any data:

```bash
bragbook demo
```

**macOS:** the first time, macOS will ask to let Terminal (and, for the background tracker, `python3` / `osascript`) control your computer. Say **OK**, or turn them on under **System Settings → Privacy & Security → Accessibility**, so Brag Book can read window titles. If `bragbook today` shows no time after a while, that permission is the usual culprit.
**Linux:** needs X11 plus `xdotool` (and `xprintidle` for idle detection). Wayland isn't supported yet.
**Windows:** works out of the box.

## Your page: http://localhost:8642

While the tracker runs (it does automatically after `autostart install`), your page lives at **http://localhost:8642**. Bookmark it, or run `bragbook dashboard` to open it. It only works on your own computer.

- **Timeline** (home): your day as a color-coded strip plus a card for each work session, in the style of [Dayflow](https://www.dayflow.so/). Each card shows what you worked on, for how long, breaks, and when Slack or email pulled you away. Use ← → to flip through past days.
- **Brag book:** wins, achievements, drafted review bullets and where your time went, by Today / Week / Month / Quarter / Year.
- **Log a win** box at the top of every page, plus **Pause 1 hour** if you need privacy.

Unlike Dayflow, it doesn't record your screen. The timeline is built from window titles, so it's lightweight and nothing leaves your Mac.

## Everyday use

| You want to… | Run |
|---|---|
| Log a win (it'll prompt you) | `bragbook win` |
| Log a win in one line | `bragbook win "Ran the ops playbook workshop" -i "4 depts aligned" -t ops` |
| Open your page | `bragbook dashboard` (or just go to http://localhost:8642) |
| See today at a glance | `bragbook today` |
| Today as a timeline, in the terminal | `bragbook timeline` (or `--date 2026-10-16`) |
| See your trophy case | `bragbook badges` |
| Build your brag book | `bragbook report --week` (or `--month`, `--quarter`, `--year`, `--from 2026-07-01`) |
| Get it as text for a doc/email | `bragbook report --quarter --format md` |
| Go private for a bit | `bragbook pause 30` · `bragbook resume` |
| Delete the last hour | `bragbook forget 60` |

Near the end of your workday you'll get one nudge if you haven't logged a win. One sentence is enough.

## What's in the brag book

1. **Wins:** what you logged, with the impact.
2. **Drafted from your activity:** bullets written for you, like *"Built and refined 3 decks (22h), including 'Fan Experience Roadmap'…"*, with a prompt to add the result.
3. **Achievements** you earned in that period.
4. **Where the time went:** hours by type of work (meetings, decks, strategy docs, data, design…).
5. **What you worked on:** each document, deck and project, with hours and days. These are the receipts.
6. **Sustainability check:** average day, late nights, weekend time, longest stretch without a break.

Click **Copy as text** to paste the whole thing anywhere.

## Achievements

| Badge | How to earn it |
|---|---|
| 🌊 Deep Dive | 90+ minutes of unbroken focus (quick Slack glances don't break it) |
| 🔥 Flow State | 4+ hours of deep work in a day |
| 🎤 Deck Builder · ✍️ Wordsmith | 2+ hours on decks / strategy docs in a day |
| 📊 Number Cruncher · 🎨 Visionary | 90+ minutes on data / design in a day |
| 🎪 Plate Spinner | 6+ different pieces of work moved forward in a day |
| 🏃 Meeting Marathoner | Survived 4+ hours of meetings |
| 🔋 Recharge Respecter | A 4h+ day with a real break at least every 2 hours |
| 🌙 Clean Shutdown | A solid day, logged off by your workday end |
| 🎩 Hat Trick · 🃏 Full House | 3+ wins in a week / a win every weekday |
| 🧭 Range | 1h+ in four kinds of deep work in a week |
| ⚙️ Steady Engine | Deep Dives on 3+ days in a week |
| 🛡️ Weekend Guardian | A full week and a quiet weekend |
| 🌱 🎶 💯 🏟️ 🏆 | 10 / 50 / 100 / 250 / 500 hours of deep work |
| 🧾 🎬 🗂️ 👑 | 1 / 10 / 25 / 50 wins logged |

## Make it yours

Run `bragbook config` to create `~/.bragbook/config.json`. In it you can change:

- **`categories`:** which apps and window titles count as Meetings, Presentations, Strategy & Writing, and so on. Add your company's tools here.
- **`exclude`:** apps and title keywords that are never recorded.
- **`workday_start` / `workday_end`**, **`break_minutes`**, **`sample_seconds`**, **`idle_seconds`**.
- **`end_of_day_nudge`** and **`notify_achievements`** (set to `false` to turn either off).

## Development

```bash
python -m unittest discover -s tests
```
