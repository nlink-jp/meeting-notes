#!/usr/bin/env python3
"""Assemble a MeetingNote JSON from per-pass work files (stdlib only).

Usage:
    assemble.py --meta work/meta.json --synthesis work/synthesis.json \\
        --items work/agenda-01.json work/agenda-02.json ... \\
        --transcript transcript.txt -o meeting.json --model claude-sonnet-5

Deterministic merge: agenda order follows the sorted item filenames,
meeting_id is derived from title:date, metadata is stamped here — the
extraction passes never produce these fields.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--meta", type=Path, required=True)
    parser.add_argument("--synthesis", type=Path)
    parser.add_argument("--items", type=Path, nargs="+", required=True)
    parser.add_argument("--transcript", type=Path)
    parser.add_argument(
        "--source-name",
        help="value for metadata.source_transcript (default: transcript filename, else 'provided')",
    )
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--model", default="claude")
    parser.add_argument("--generated-by", default="meeting-notes (Claude Code skill)")
    args = parser.parse_args()

    note = load(args.meta)
    note["agenda"] = [load(p) for p in sorted(args.items)]

    if args.synthesis:
        synthesis = load(args.synthesis)
        note["participant_dynamics"] = synthesis.get("participant_dynamics", [])
        note["key_takeaways"] = synthesis.get("key_takeaways", [])

    if not note.get("meeting_id"):
        try:
            date_iso = parse_datetime(note["date"]).isoformat()
        except (KeyError, ValueError) as e:
            print(f"ERROR: meta.json needs a valid ISO 8601 'date' to derive meeting_id: {e}")
            return 1
        seed = f"{note.get('title', '')}:{date_iso}"
        note["meeting_id"] = hashlib.sha256(seed.encode()).hexdigest()[:12]

    source_name = args.source_name
    if args.transcript:
        note["raw_transcript"] = args.transcript.read_text(encoding="utf-8")
        source_name = source_name or args.transcript.name

    note["metadata"] = {
        "source_audio": "",
        "source_transcript": source_name or "provided",
        "generated_by": args.generated_by,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
    }

    args.output.write_text(
        json.dumps(note, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"assembled: {args.output} ({len(note['agenda'])} agenda items)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
