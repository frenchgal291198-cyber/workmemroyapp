# Know Your Neighbors

An opt-in Slack tool that connects BKSE corporate colleagues by home neighborhood first and shared interests second. This repo is the working prototype behind the People & Culture proposal.

**What's in it**

| Part | Where | Status |
| --- | --- | --- |
| Matching engine (neighborhood → nearby → borough → restaurants → interests, never repeats a pair, odd counts form one trio) | `src/matching.js` | Real, tested |
| Pilot metrics (opt-in rate, directory usage, match acknowledgment) from an event log | `src/metrics.js` | Real, tested |
| Slack app: `/neighbors` slash command, profile modal, directory, match DMs with a "We met" button, App Home dashboard | `src/slack/` | Scaffolded, needs a Slack workspace to run |
| Clickable web demo that stands in for the Slack UI | `demo/template.html` → `dist/index.html` | Ready to show |

Every person in the sample data is fictional.

## Try the demo

```
npm install
npm run demo        # builds dist/index.html and serves it at http://localhost:4173
```

Or just run `npm run build:demo` and open `dist/index.html` in a browser. It works offline. Your edits persist in the browser; "Reset demo data" puts it back to Day 38 of the pilot.

## Run the tests

```
npm test
```

## Run it in Slack

1. Create a Slack app (from scratch) with a bot token scoped to `commands`, `chat:write`, `im:write`, `mpim:write`, `users:read`, and enable Socket Mode plus the App Home tab and the `app_home_opened` event.
2. Add a slash command `/neighbors`.
3. Set the environment:

```
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
SLACK_APP_TOKEN=xapp-...        # Socket Mode
KYN_ADMINS=U0123ABC,U0456DEF    # who can run a match cycle
KYN_ELIGIBLE_HEADCOUNT=140      # for the opt-in rate
```

4. `npm run slack` to start. `npm run cycle` runs a match cycle from cron every two weeks (without a token it prints a dry run).

Commands inside Slack:

- `/neighbors profile` joins the pilot or edits your neighborhood and interests
- `/neighbors directory [neighborhood | interest | department]` browses who's near you
- `/neighbors leave` opts out and hides your profile immediately
- `/neighbors cycle` runs a match cycle (admins only)

## How matching works

Each pair gets a score; the cycle pairs everyone greedily from the best score down, so the strongest reasons to talk get paired first.

| Signal | Points |
| --- | --- |
| Same neighborhood | +10 |
| Nearby neighborhood (same area, e.g. Park Slope and Prospect Heights) | +6 |
| Same borough | +3 |
| Each shared favorite restaurant | +3 |
| Each shared interest | +2 |
| Different departments | +1 |
| Same department | −2 |
| Already matched in an earlier cycle | never |

Storage is one JSON file (`data/store.json`), which is enough for a 90-day pilot of about 150 people.
