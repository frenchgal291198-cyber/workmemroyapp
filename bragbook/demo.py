"""Fill a separate demo database with three weeks of realistic activity, so you can see a report today."""

import random
from datetime import date, datetime, time as dtime, timedelta

SAMPLE = 60  # one demo sample per minute

WORK = [
    ("Microsoft PowerPoint", "2027 Fan Experience Roadmap.pptx - PowerPoint"),
    ("Microsoft PowerPoint", "Premium Seating Activation - Sponsor Pitch.pptx - PowerPoint"),
    ("Google Chrome", "Board Offsite: Venue of the Future - Google Slides - Google Chrome"),
    ("Google Chrome", "Season Ticket Holder Journey - Strategy Brief - Google Docs - Google Chrome"),
    ("Google Chrome", "Concert Night Ops Playbook - Google Docs - Google Chrome"),
    ("Notion", "Q4 Guest Experience OKRs"),
    ("Microsoft Excel", "Concessions Wait-Time Analysis.xlsx - Excel"),
    ("Google Chrome", "NPS by Section - Post-Event Survey - Google Sheets - Google Chrome"),
    ("Figma", "Concourse Wayfinding Concepts - Figma"),
    ("Miro", "Gameday Guest Journey Map - Miro"),
    ("Google Chrome", "Arena Renovation Program - Smartsheet - Google Chrome"),
]
MEETINGS = [("zoom.us", "Zoom Meeting"), ("Google Chrome", "Meet - wkly-exp-sync - Google Chrome")]
COMMS = [("Slack", "ops-gameday (Channel) - Venue Co - Slack"), ("Microsoft Outlook", "Inbox - Outlook")]
BROWSE = [("Google Chrome", "Stadium tech trends 2027 - Google Search - Google Chrome")]

WINS = [
    (2, "Presented the 2027 Fan Experience Roadmap to the exec team", "3 pilots greenlit for next season", "strategy, exec"),
    (5, "Closed the premium seating activation pitch with our beverage partner", "$1.2M sponsorship renewed", "partnerships"),
    (8, "Built the concessions wait-time model from POS data", "Found 2 stands driving 40% of queues", "analysis, ops"),
    (11, "Ran the concert-night ops playbook workshop with 4 departments", "", "ops, alignment"),
    (15, "Shipped the concourse wayfinding concepts to design partner", "Signage RFP out 2 weeks early", "design"),
    (16, "Turned post-event NPS into a section-by-section action plan", "NPS +6 in upper bowl pilot", "fans, data"),
    (18, "Got board sign-off on the Venue of the Future offsite agenda", "", "exec"),
]


def seed(db, days: int = 21, today: date = None):
    rng = random.Random(42)
    today = today or date.today()
    rows = []
    for back in range(days, 0, -1):
        d = today - timedelta(days=back)
        if d.weekday() >= 5:
            if rng.random() < 0.3:  # the occasional weekend email check
                t = datetime.combine(d, dtime(10, 0)).timestamp()
                rows += [(t + i * SAMPLE, SAMPLE, *COMMS[1]) for i in range(20)]
            continue
        t = datetime.combine(d, dtime(8, 45)).timestamp() + rng.randint(0, 30) * 60
        late = rng.random() < 0.3
        end = datetime.combine(d, dtime(19, 30) if late else dtime(17, 45)).timestamp()
        focus = rng.sample(WORK, 3)
        lunch = False
        while t < end:
            kind = rng.random()
            if kind < 0.45:
                app, title = rng.choice(focus)
                minutes = rng.randint(35, 110)
            elif kind < 0.7:
                app, title = rng.choice(MEETINGS)
                minutes = rng.choice([30, 30, 45, 60])
            elif kind < 0.9:
                app, title = rng.choice(COMMS)
                minutes = rng.randint(5, 25)
            else:
                app, title = BROWSE[0]
                minutes = rng.randint(5, 20)
            for i in range(minutes):
                if t >= end:
                    break
                rows.append((t, SAMPLE, app, title))
                # quick Slack glances mid-focus
                if rng.random() < 0.02:
                    t += SAMPLE
                    rows.append((t, SAMPLE, *COMMS[0]))
                t += SAMPLE
            if rng.random() < 0.35 or (not lunch and datetime.fromtimestamp(t).hour >= 12):
                lunch = lunch or datetime.fromtimestamp(t).hour >= 12
                t += rng.randint(10, 45) * 60  # a real break
    db.add_samples(rows)
    for back, text, impact, tags in WINS:
        if back <= days:
            d = today - timedelta(days=days - back)
            d -= timedelta(days=max(0, d.weekday() - 4))  # weekend wins land on Friday
            ts = datetime.combine(d, dtime(16, 30)).timestamp()
            db.add_win(text, impact, tags, ts=ts)
