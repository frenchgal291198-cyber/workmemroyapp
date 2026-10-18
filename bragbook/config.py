"""Settings. Everything lives in ~/.bragbook (or $BRAGBOOK_HOME) and never leaves your machine."""

import copy
import json
import os
from pathlib import Path

# Categories are checked in order. A window matches a category when its title
# contains one of `title_keywords` (case-insensitive), or, failing any title
# match, when its app name matches one of `apps`.
DEFAULT_CATEGORIES = [
    {
        "name": "Meetings",
        "apps": ["zoom.us", "zoom", "webex", "facetime", "gotomeeting"],
        "title_keywords": ["zoom meeting", "google meet", "meet - ", "meet.google.com",
                           "teams meeting", "| microsoft teams meeting", "webex"],
    },
    {
        "name": "Communication",
        "apps": ["slack", "mail", "outlook", "messages", "microsoft teams", "teams",
                 "ms-teams", "discord", "whatsapp", "superhuman", "spark"],
        "title_keywords": [" - gmail", "- outlook", "| outlook", " - slack", "| slack"],
    },
    {
        "name": "Presentations",
        "apps": ["powerpoint", "microsoft powerpoint", "powerpnt", "keynote", "pitch"],
        "title_keywords": ["- google slides", ".pptx", ".ppt", "pitch.com"],
    },
    {
        "name": "Strategy & Writing",
        "apps": ["word", "microsoft word", "winword", "pages", "notion", "obsidian",
                 "bear", "craft", "ulysses", "scrivener"],
        "title_keywords": ["- google docs", ".docx", "- notion", "| notion",
                           "confluence", "coda"],
    },
    {
        "name": "Data & Analysis",
        "apps": ["excel", "microsoft excel", "numbers", "tableau", "power bi", "pbidesktop"],
        "title_keywords": ["- google sheets", ".xlsx", ".xls", ".csv", "tableau", "power bi",
                           "looker", "data studio"],
    },
    {
        "name": "Design & Visual",
        "apps": ["figma", "photoshop", "illustrator", "indesign", "sketch", "canva",
                 "miro", "affinity", "lucid", "whimsical"],
        "title_keywords": ["figma", "canva", "miro", "lucidchart", "figjam", "whimsical"],
    },
    {
        "name": "Planning & Projects",
        "apps": ["asana", "monday", "trello", "jira", "linear", "smartsheet", "airtable",
                 "clickup", "omnifocus", "things", "todoist", "project"],
        "title_keywords": ["asana", "monday.com", "trello", "jira", "linear", "smartsheet",
                           "airtable", "clickup", "basecamp"],
    },
    {
        "name": "Building & Code",
        "apps": ["code", "visual studio code", "cursor", "pycharm", "intellij", "xcode",
                 "terminal", "iterm2", "windowsterminal", "warp", "sublime_text"],
        "title_keywords": ["visual studio code", "github.com", "claude code"],
    },
    {
        "name": "Research & Browsing",
        "apps": ["google chrome", "chrome", "safari", "firefox", "msedge", "microsoft edge",
                 "arc", "brave", "brave browser", "opera", "vivaldi"],
        "title_keywords": [],
    },
]

# The categories that count as "making things" for focus and deep-work badges.
DEFAULT_DEEP_WORK = [
    "Presentations", "Strategy & Writing", "Data & Analysis", "Design & Visual",
    "Planning & Projects", "Building & Code",
]

DEFAULTS = {
    # How often to look at the active window.
    "sample_seconds": 15,
    # No keyboard/mouse input for this long = you're away, don't count it.
    "idle_seconds": 300,
    # Used by the "Clean Shutdown" badge and the end-of-day nudge.
    "workday_start": "08:30",
    "workday_end": "18:30",
    # A gap at least this long counts as a real break.
    "break_minutes": 10,
    # Send a desktop nudge near workday_end if you haven't logged a win today.
    "end_of_day_nudge": True,
    # Show desktop notifications when you unlock an achievement.
    "notify_achievements": True,
    # The dashboard page lives at http://localhost:<port> while the tracker runs.
    "dashboard_port": 8642,
    # Never record windows from these apps, or whose titles contain these words.
    "exclude": {
        "apps": ["1password", "keychain access", "bitwarden", "lastpass", "dashlane"],
        "title_keywords": ["private browsing", "incognito", "inprivate", "bank", "password"],
    },
    "categories": DEFAULT_CATEGORIES,
    "deep_work_categories": DEFAULT_DEEP_WORK,
}


def home() -> Path:
    path = Path(os.environ.get("BRAGBOOK_HOME") or Path.home() / ".bragbook")
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return home() / "config.json"


def db_path() -> Path:
    return home() / "bragbook.db"


def load() -> dict:
    cfg = copy.deepcopy(DEFAULTS)
    path = config_path()
    if path.exists():
        with open(path, encoding="utf-8") as f:
            cfg.update(json.load(f))
    return cfg


def write_defaults(force: bool = False) -> Path:
    path = config_path()
    if force or not path.exists():
        with open(path, "w", encoding="utf-8") as f:
            json.dump(DEFAULTS, f, indent=2)
    return path
