#!/usr/bin/env python3
"""Behaviour tests for the bundled scripts (stdlib only, run via make check).

The fixture pair sample-meeting.{txt,json} is real output from the
predecessor meeting-note CLI — it doubles as a format-compatibility check.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "meeting-notes" / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

SAMPLE_JSON = FIXTURES / "sample-meeting.json"
SAMPLE_TXT = FIXTURES / "sample-meeting.txt"


def run(script: str, *args: object) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *map(str, args)],
        capture_output=True,
        text=True,
    )


def sample() -> dict:
    return json.loads(SAMPLE_JSON.read_text(encoding="utf-8"))


class ValidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def write(self, name: str, data: dict) -> Path:
        path = self.dir / name
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def test_full_ok_on_cli_produced_record(self) -> None:
        result = run("validate.py", SAMPLE_JSON)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)

    def test_missing_required_field(self) -> None:
        note = sample()
        del note["title"]
        result = run("validate.py", self.write("note.json", note))
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing required field 'title'", result.stdout)

    def test_bad_enum(self) -> None:
        note = sample()
        note["agenda"][0]["status"] = "approved"
        result = run("validate.py", self.write("note.json", note))
        self.assertEqual(result.returncode, 1)
        self.assertIn("$.agenda[0].status", result.stdout)

    def test_bad_type(self) -> None:
        note = sample()
        note["duration_seconds"] = "3600"
        result = run("validate.py", self.write("note.json", note))
        self.assertEqual(result.returncode, 1)
        self.assertIn("$.duration_seconds", result.stdout)

    def test_bad_datetime(self) -> None:
        note = sample()
        note["date"] = "next Tuesday"
        result = run("validate.py", self.write("note.json", note))
        self.assertEqual(result.returncode, 1)
        self.assertIn("ISO 8601", result.stdout)

    def test_invalid_json_input(self) -> None:
        path = self.dir / "broken.json"
        path.write_text('{"title": ', encoding="utf-8")
        result = run("validate.py", path)
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid JSON", result.stdout)

    def test_part_item(self) -> None:
        item = sample()["agenda"][0]
        result = run("validate.py", "--part", "item", self.write("item.json", item))
        self.assertEqual(result.returncode, 0, result.stdout)

        del item["status"]
        result = run("validate.py", "--part", "item", self.write("item2.json", item))
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing required field 'status'", result.stdout)

    def test_part_meta(self) -> None:
        note = sample()
        meta = {
            k: note[k]
            for k in ("title", "date", "duration_seconds", "meeting_type", "context", "participants")
        }
        result = run("validate.py", "--part", "meta", self.write("meta.json", meta))
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_part_synthesis(self) -> None:
        note = sample()
        synthesis = {
            "participant_dynamics": note["participant_dynamics"],
            "key_takeaways": note["key_takeaways"],
        }
        result = run("validate.py", "--part", "synthesis", self.write("syn.json", synthesis))
        self.assertEqual(result.returncode, 0, result.stdout)

        synthesis["participant_dynamics"][0]["relation"] = "friendship"
        result = run("validate.py", "--part", "synthesis", self.write("syn2.json", synthesis))
        self.assertEqual(result.returncode, 1)


class QuoteCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.transcript = self.dir / "t.txt"
        self.transcript.write_text(
            "田中: 本日の議題はエスカレーション基準の見直しです。\n"
            "鈴木: 到達数ベースの自動エスカレーションを提案します。\n",
            encoding="utf-8",
        )

    def note_with(self, *texts: str) -> Path:
        note = {
            "meeting_id": "x",
            "title": "t",
            "date": "2026-04-07T10:00:00Z",
            "participants": [],
            "agenda": [
                {
                    "title": "a",
                    "status": "decided",
                    "utterances": [{"speaker": "田中", "text": t} for t in texts],
                }
            ],
            "metadata": {"generated_by": "test", "generated_at": "2026-04-07T11:00:00Z", "model": "m"},
        }
        path = self.dir / "note.json"
        path.write_text(json.dumps(note, ensure_ascii=False), encoding="utf-8")
        return path

    def test_verbatim_quote_passes(self) -> None:
        path = self.note_with("本日の議題はエスカレーション基準の見直しです。")
        result = run("validate.py", path, "--transcript", self.transcript)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("WARN", result.stdout)

    def test_fabricated_quote_warns(self) -> None:
        path = self.note_with("予算は無制限で承認されました。")
        result = run("validate.py", path, "--transcript", self.transcript)
        self.assertEqual(result.returncode, 0)
        self.assertIn("WARN", result.stdout)
        self.assertIn("quote not found", result.stdout)

    def test_strict_makes_warning_fatal(self) -> None:
        path = self.note_with("予算は無制限で承認されました。")
        result = run("validate.py", path, "--transcript", self.transcript, "--strict")
        self.assertEqual(result.returncode, 2)

    def test_whitespace_differences_tolerated(self) -> None:
        path = self.note_with("本日の議題は\nエスカレーション基準の見直しです。")
        result = run("validate.py", path, "--transcript", self.transcript)
        self.assertNotIn("WARN", result.stdout)

    def test_short_quotes_skipped(self) -> None:
        path = self.note_with("はい。")
        result = run("validate.py", path, "--transcript", self.transcript)
        self.assertNotIn("WARN", result.stdout)


class AssembleTests(unittest.TestCase):
    def test_roundtrip_matches_cli_record(self) -> None:
        """Split the CLI-produced sample into work files, reassemble, and
        confirm the parts and the derived meeting_id come back identical."""
        note = sample()
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            meta = {
                k: note[k]
                for k in ("title", "date", "duration_seconds", "meeting_type", "context", "participants")
            }
            (work / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
            (work / "synthesis.json").write_text(
                json.dumps(
                    {
                        "participant_dynamics": note["participant_dynamics"],
                        "key_takeaways": note["key_takeaways"],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            item_paths = []
            for i, item in enumerate(note["agenda"], 1):
                p = work / f"agenda-{i:02d}.json"
                p.write_text(json.dumps(item, ensure_ascii=False), encoding="utf-8")
                item_paths.append(p)

            out = work / "out.json"
            result = run(
                "assemble.py",
                "--meta", work / "meta.json",
                "--synthesis", work / "synthesis.json",
                "--items", *item_paths,
                "--transcript", SAMPLE_TXT,
                "-o", out,
                "--model", "test-model",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            assembled = json.loads(out.read_text(encoding="utf-8"))
            # Same derivation as the CLI: SHA-256("title:date.isoformat()")[:12]
            self.assertEqual(assembled["meeting_id"], note["meeting_id"])
            self.assertEqual(assembled["agenda"], note["agenda"])
            self.assertEqual(assembled["participant_dynamics"], note["participant_dynamics"])
            self.assertEqual(
                assembled["raw_transcript"], SAMPLE_TXT.read_text(encoding="utf-8")
            )
            self.assertEqual(assembled["metadata"]["model"], "test-model")
            self.assertEqual(assembled["metadata"]["source_transcript"], "sample-meeting.txt")

            # The assembled record passes full validation.
            result = run("validate.py", out)
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_missing_date_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            (work / "meta.json").write_text('{"title": "t"}', encoding="utf-8")
            (work / "a.json").write_text('{"title": "a", "status": "decided"}', encoding="utf-8")
            result = run(
                "assemble.py", "--meta", work / "meta.json",
                "--items", work / "a.json", "-o", work / "out.json",
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("date", result.stdout)


class CompileTests(unittest.TestCase):
    def test_markdown_ja(self) -> None:
        result = run("compile.py", SAMPLE_JSON)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("# セキュリティインシデント対応体制 定例会議", result.stdout)
        self.assertIn("## 議題", result.stdout)
        self.assertIn("#### アクションアイテム", result.stdout)
        self.assertIn("[決定]", result.stdout)

    def test_markdown_en(self) -> None:
        result = run("compile.py", SAMPLE_JSON, "--lang", "en")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("## Agenda", result.stdout)
        self.assertIn("[Decided]", result.stdout)
        self.assertNotIn("## 議題", result.stdout)

    def test_html_self_contained_and_escaped(self) -> None:
        note = sample()
        note["title"] = 'A <script>alert("x")</script> meeting'
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "note.json"
            src.write_text(json.dumps(note, ensure_ascii=False), encoding="utf-8")
            out = Path(tmp) / "note.html"
            result = run("compile.py", src, "-f", "html", "-o", out)
            self.assertEqual(result.returncode, 0, result.stderr)
            html_text = out.read_text(encoding="utf-8")
        self.assertIn("<!DOCTYPE html>", html_text)
        self.assertIn("&lt;script&gt;", html_text)
        self.assertNotIn("<script>", html_text)
        self.assertIn("badge-decided", html_text)
        self.assertIn("参加者間の関係性", html_text)

    def test_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.md"
            result = run("compile.py", SAMPLE_JSON, "-o", out)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out.exists())
            self.assertIn("compiled:", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
