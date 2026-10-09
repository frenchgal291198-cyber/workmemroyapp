import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime, time as dtime, timedelta
from pathlib import Path

from bragbook import achievements, analysis as A, config, demo, report
from bragbook.categorize import app_matches, categorize, extract_artifact, is_excluded
from bragbook.db import DB

def cfg():
    os.environ["BRAGBOOK_HOME"] = tempfile.mkdtemp()
    return config.load()


def at(d: date, hh: int, mm: int = 0) -> float:
    return datetime.combine(d, dtime(hh, mm)).timestamp()


def fill(db, start: float, minutes: int, app: str, title: str, step: int = 60):
    db.add_samples([(start + i * step, step, app, title) for i in range(minutes * 60 // step)])


class CategorizeTests(unittest.TestCase):
    def setUp(self):
        self.cats = cfg()["categories"]

    def test_word_does_not_match_password_managers(self):
        self.assertTrue(app_matches("Microsoft Word", ["word"]))
        self.assertTrue(app_matches("WINWORD.EXE", ["winword"]))
        self.assertFalse(app_matches("1Password", ["word"]))

    def test_browser_titles_beat_browser_app(self):
        self.assertEqual(categorize("Google Chrome", "Plan - Google Docs - Google Chrome", self.cats),
                         "Strategy & Writing")
        self.assertEqual(categorize("Google Chrome", "Meet - abc-defg-hij - Google Chrome", self.cats), "Meetings")
        self.assertEqual(categorize("Google Chrome", "Some article - Google Chrome", self.cats),
                         "Research & Browsing")

    def test_native_apps(self):
        self.assertEqual(categorize("POWERPNT", "Deck.pptx - PowerPoint", self.cats), "Presentations")
        self.assertEqual(categorize("zoom.us", "Zoom Meeting", self.cats), "Meetings")
        self.assertEqual(categorize("Slack", "general - Slack", self.cats), "Communication")
        self.assertEqual(categorize("Mystery", "", self.cats), "Other")

    def test_meeting_notes_doc_is_not_a_meeting(self):
        self.assertEqual(categorize("Google Chrome", "Meeting notes - Google Docs - Google Chrome", self.cats),
                         "Strategy & Writing")

    def test_extract_artifact(self):
        self.assertEqual(extract_artifact("Microsoft PowerPoint", "Fan Roadmap - v2.pptx - PowerPoint",
                                          "Presentations"), "Fan Roadmap - v2")
        self.assertEqual(extract_artifact("Google Chrome", "Budget - Google Sheets - Google Chrome",
                                          "Data & Analysis"), "Budget")
        self.assertEqual(extract_artifact("Code", "● app.py - myproj - Visual Studio Code", "Building & Code"),
                         "myproj")
        self.assertIsNone(extract_artifact("Google Chrome", "Untitled document - Google Docs - Google Chrome",
                                           "Strategy & Writing"))
        self.assertEqual(extract_artifact("Microsoft Word", "Report.docx [Read-Only] - Word", ""), "Report.docx")

    def test_exclusions(self):
        ex = cfg()["exclude"]
        self.assertTrue(is_excluded("1Password 8", "Vault", ex))
        self.assertTrue(is_excluded("Google Chrome", "Chase Bank - Google Chrome", ex))
        self.assertFalse(is_excluded("Google Chrome", "Docs", ex))


class AnalysisTests(unittest.TestCase):
    def s(self, ts, cat, dur=60):
        return A.Sample(ts, dur, "app", "t", cat, None)

    def test_focus_run_survives_short_interruption(self):
        deep = {"Presentations"}
        samples = [self.s(i * 60, "Presentations") for i in range(60)]
        samples.append(self.s(60 * 60, "Communication"))           # 1 min Slack
        samples += [self.s((61 + i) * 60, "Presentations") for i in range(40)]
        runs = A.focus_runs(samples, deep)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0].seconds, 100 * 60)

    def test_focus_run_breaks_on_meeting_or_gap(self):
        deep = {"Presentations"}
        samples = [self.s(i * 60, "Presentations") for i in range(30)]
        samples += [self.s((30 + i) * 60, "Meetings") for i in range(30)]
        samples += [self.s((60 + i) * 60, "Presentations") for i in range(30)]
        samples += [self.s((200 + i) * 60, "Presentations") for i in range(30)]  # after a gap
        self.assertEqual(len(A.focus_runs(samples, deep)), 3)

    def test_longest_without_break(self):
        samples = [self.s(i * 60, "x") for i in range(90)]
        samples += [self.s((100 + i) * 60, "x") for i in range(30)]  # 10 min break before this
        self.assertEqual(A.longest_without_break(samples, 600), 90 * 60)


class AchievementTests(unittest.TestCase):
    def setUp(self):
        self.cfg = cfg()
        self.db = DB(config.db_path())
        self.today = date(2026, 10, 8)  # a Thursday
        self.yesterday = self.today - timedelta(days=1)

    def unlocked(self):
        return {u["achievement_id"] for u in self.db.all_unlocks()}

    def test_deep_dive_and_deck_builder(self):
        fill(self.db, at(self.today, 9), 130, "Microsoft PowerPoint", "Deck.pptx - PowerPoint")
        new = achievements.evaluate(self.db, self.cfg, self.today, self.today, today=self.today)
        ids = {u.achievement.id for u in new}
        self.assertIn("deep_dive", ids)
        self.assertIn("deck_builder", ids)
        self.assertIn("“Deck”", next(u.detail for u in new if u.achievement.id == "deck_builder"))

    def test_unlocks_only_once_per_period(self):
        fill(self.db, at(self.today, 9), 130, "Microsoft PowerPoint", "Deck.pptx - PowerPoint")
        achievements.evaluate(self.db, self.cfg, self.today, self.today, today=self.today)
        again = achievements.evaluate(self.db, self.cfg, self.today, self.today, today=self.today)
        self.assertEqual(again, [])

    def test_end_of_day_badges_wait_until_day_is_over(self):
        for start in (9, 11, 14):
            fill(self.db, at(self.today, start), 100, "Microsoft Word", "Plan.docx - Word")
        achievements.evaluate(self.db, self.cfg, self.today, self.today, today=self.today)
        self.assertNotIn("clean_shutdown", self.unlocked())
        self.assertNotIn("recharge", self.unlocked())
        achievements.evaluate(self.db, self.cfg, self.today, self.today, today=self.today + timedelta(days=1))
        self.assertIn("clean_shutdown", self.unlocked())
        self.assertIn("recharge", self.unlocked())

    def test_late_night_blocks_clean_shutdown(self):
        fill(self.db, at(self.yesterday, 9), 240, "Microsoft Word", "Plan.docx - Word")
        fill(self.db, at(self.yesterday, 21), 30, "Slack", "general - Slack")
        achievements.evaluate(self.db, self.cfg, self.yesterday, self.yesterday, today=self.today)
        self.assertNotIn("clean_shutdown", self.unlocked())
        self.assertNotIn("recharge", self.unlocked())  # 4h straight, no break

    def test_win_badges(self):
        for i in range(3):
            self.db.add_win(f"win {i}", ts=at(self.today - timedelta(days=i), 16))
        achievements.evaluate(self.db, self.cfg, self.today - timedelta(days=3), self.today, today=self.today)
        self.assertIn("wins_1", self.unlocked())
        self.assertIn("hat_trick", self.unlocked())
        self.assertNotIn("wins_10", self.unlocked())


class ReportTests(unittest.TestCase):
    def test_demo_report_renders(self):
        c = cfg()
        db = DB(config.db_path())
        today = date.today()
        demo.seed(db, today=today)
        data = report.build(db, c, today - timedelta(days=21), today, "Demo")
        self.assertEqual(len(data.wins), len(demo.WINS))
        self.assertTrue(data.badges)
        self.assertTrue(any(b.source == "draft" for b in data.bullets))
        html = report.to_html(data)
        self.assertIn("Fan Experience Roadmap", html)
        self.assertNotIn("</script>\n</body>", html.split("const md")[1].split(";")[0])
        md = report.to_markdown(data)
        self.assertIn("## Wins", md)

    def test_html_escapes_user_text(self):
        c = cfg()
        db = DB(config.db_path())
        db.add_win("<script>alert(1)</script> & co", impact="</script>")
        first, last, label = report.period("today")
        out = report.to_html(report.build(db, c, first, last, label))
        self.assertNotIn("<script>alert", out)
        self.assertEqual(out.count("</script>"), 1)

    def test_periods(self):
        d = date(2026, 10, 8)
        self.assertEqual(report.period("week", d)[0], date(2026, 10, 5))
        self.assertEqual(report.period("quarter", d)[0], date(2026, 10, 1))
        self.assertEqual(report.period("quarter", d)[2], "Q4 2026")


class CliTests(unittest.TestCase):
    def test_win_and_wins(self):
        from bragbook.cli import main
        cfg()
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["win", "Launched", "the", "pilot", "-i", "queues -20%", "-t", "ops"])
            main(["wins", "--today"])
            main(["report", "--today", "--no-open", "-o", str(Path(os.environ["BRAGBOOK_HOME"]) / "r.html")])
        out = buf.getvalue()
        self.assertIn("Logged win #1", out)
        self.assertIn("First Receipt", out)
        self.assertIn("Launched the pilot", out)
        self.assertTrue((Path(os.environ["BRAGBOOK_HOME"]) / "r.html").exists())


if __name__ == "__main__":
    unittest.main()
