"""Turn raw (app, window title) pairs into a category and the thing you were working on."""

import re
from typing import Iterable, Optional

# Window-title segments that name an app, browser or status rather than your work.
NOISE = {
    "google chrome", "chrome", "safari", "mozilla firefox", "firefox", "microsoft edge", "edge",
    "arc", "brave", "opera", "vivaldi", "google docs", "google slides", "google sheets",
    "google drive", "powerpoint", "microsoft powerpoint", "word", "microsoft word", "excel",
    "microsoft excel", "keynote", "pages", "numbers", "figma", "canva", "miro", "notion",
    "confluence", "airtable", "asana", "monday.com", "trello", "jira", "smartsheet", "linear",
    "visual studio code", "cursor", "tableau", "power bi", "lucidchart", "figjam",
    "saved", "saved to this pc", "saved to onedrive", "saved to sharepoint", "autosaved",
    "read-only", "compatibility mode", "edited", "personal", "work", "profile 1", "profile 2",
}

# Titles that don't name a real piece of work.
GENERIC = {
    "untitled", "new tab", "home", "inbox", "start", "start page", "recent", "drafts",
    "dashboard", "presentation1", "document1", "book1", "untitled presentation",
    "untitled document", "untitled spreadsheet", "untitled design", "my drive", "shared with me",
}

FILE_EXT = re.compile(
    r"\.(pptx?|key|docx?|pages|xlsx?|xlsm|csv|numbers|pdf|fig|sketch|psd|ai|indd|md|txt)$", re.I)
SEPARATORS = re.compile(r"\s+[-–—|]\s+")
MORE_TABS = re.compile(r"\s+and \d+ more pages?$", re.I)  # Edge: "Doc - Google Docs and 3 more pages"


def norm_app(app: str) -> str:
    a = (app or "").strip().lower()
    return a[:-4] if a.endswith(".exe") else a


def app_matches(app: str, keys: Iterable[str]) -> bool:
    """Match whole app names or whole words, so 'word' matches 'Microsoft Word' but not '1Password'."""
    a = norm_app(app)
    if not a:
        return False
    tokens = set(re.split(r"[\s._-]+", a))
    for key in keys:
        k = key.lower()
        if a == k or a.startswith(k + " ") or a.startswith(k + ".") or k in tokens:
            return True
    return False


def categorize(app: str, title: str, categories: list) -> str:
    t = (title or "").lower()
    if t:
        for cat in categories:
            if any(kw.lower() in t for kw in cat.get("title_keywords", [])):
                return cat["name"]
    for cat in categories:
        if app_matches(app, cat.get("apps", [])):
            return cat["name"]
    return "Other"


def is_excluded(app: str, title: str, exclude: dict) -> bool:
    if app_matches(app, exclude.get("apps", [])):
        return True
    t = (title or "").lower()
    return any(kw.lower() in t for kw in exclude.get("title_keywords", []))


def extract_artifact(app: str, title: str, category: str) -> Optional[str]:
    """Pull the document / deck / project name out of a window title."""
    t = (title or "").strip().lstrip("●•*◉ ").strip()
    if not t:
        return None
    app_l = norm_app(app)
    parts = [MORE_TABS.sub("", p).strip() for p in SEPARATORS.split(t)]
    parts = [p for p in parts if p]
    noise = lambda p: p.lower() in NOISE or p.lower() == app_l
    if category == "Building & Code":
        # Code editors show "file - project"; the project is the more useful name.
        kept = [p for p in parts if not noise(p)]
        name = kept[1] if len(kept) >= 2 else (kept[0] if kept else "")
    else:
        # Everything before the first app/browser segment is the document name,
        # so "Plan - Sponsor Pitch.pptx - PowerPoint" keeps its full name.
        lead = []
        for p in parts:
            if noise(p):
                break
            lead.append(p)
        if not lead:
            lead = [p for p in parts if not noise(p)][:1]
        name = " - ".join(lead)
    if not name:
        return None
    name = FILE_EXT.sub("", name)
    name = re.sub(r"\s*\[[^\]]*\]\s*$", "", name)      # [Compatibility Mode], [Read-Only]
    name = re.sub(r"\s*\(\d+\)\s*$", "", name).strip()  # "Inbox (3)"
    if len(name) < 3 or name.lower() in GENERIC:
        return None
    return name[:80]
