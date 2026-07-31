#!/usr/bin/env python3
"""Validate meeting-notes JSON against the bundled schema (stdlib only).

Usage:
    validate.py meeting.json                        # full MeetingNote
    validate.py --part meta work/meta.json          # top-level skeleton
    validate.py --part item work/agenda-01.json     # one agenda item
    validate.py --part synthesis work/synthesis.json
    validate.py meeting.json --transcript t.txt     # + verbatim-quote check

Schema errors are printed as "ERROR: <path>: <message>" and exit 1.
Quote mismatches are printed as "WARN: ..." and exit 0 (2 with --strict).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.json"

# Minimum normalized length for a quote to be checked — anything shorter
# (e.g. "はい。") matches almost any transcript and proves nothing.
MIN_QUOTE_CHARS = 6


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def check(value: object, schema: dict, path: str, errors: list[str]) -> None:
    """Validate value against the subset of JSON Schema used by schema.json:
    type (object/array/string/integer), required, properties, items, enum,
    format: date-time."""
    t = schema.get("type")
    if t == "object":
        if not isinstance(value, dict):
            errors.append(f"{path}: expected object, got {type(value).__name__}")
            return
        for req in schema.get("required", []):
            if req not in value:
                errors.append(f"{path}: missing required field '{req}'")
        for key, sub in schema.get("properties", {}).items():
            if key in value:
                check(value[key], sub, f"{path}.{key}", errors)
    elif t == "array":
        if not isinstance(value, list):
            errors.append(f"{path}: expected array, got {type(value).__name__}")
            return
        items = schema.get("items")
        if items:
            for i, v in enumerate(value):
                check(v, items, f"{path}[{i}]", errors)
    elif t == "string":
        if not isinstance(value, str):
            errors.append(f"{path}: expected string, got {type(value).__name__}")
            return
        enum = schema.get("enum")
        if enum and value not in enum:
            errors.append(f"{path}: '{value}' is not one of {enum}")
        if schema.get("format") == "date-time" and value:
            try:
                parse_datetime(value)
            except ValueError:
                errors.append(f"{path}: '{value}' is not an ISO 8601 date-time")
    elif t == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"{path}: expected integer, got {type(value).__name__}")


def part_schema(schema: dict, part: str) -> dict:
    props = schema["properties"]
    if part == "full":
        return schema
    if part == "item":
        return props["agenda"]["items"]
    if part == "meta":
        exclude = {
            "meeting_id",
            "agenda",
            "participant_dynamics",
            "key_takeaways",
            "raw_transcript",
            "metadata",
        }
        return {
            "type": "object",
            "required": ["title", "date", "participants"],
            "properties": {k: v for k, v in props.items() if k not in exclude},
        }
    if part == "synthesis":
        return {
            "type": "object",
            "required": ["participant_dynamics", "key_takeaways"],
            "properties": {
                "participant_dynamics": props["participant_dynamics"],
                "key_takeaways": props["key_takeaways"],
            },
        }
    raise ValueError(f"unknown part: {part}")


def normalize(text: str) -> str:
    """Collapse all whitespace so near-verbatim quotes survive line wrapping."""
    return re.sub(r"\s+", "", text)


def check_quotes(note: dict, transcript: str) -> list[str]:
    warnings: list[str] = []
    haystack = normalize(transcript)
    for i, item in enumerate(note.get("agenda", [])):
        for j, utt in enumerate(item.get("utterances", [])):
            text = utt.get("text", "")
            needle = normalize(text)
            if len(needle) < MIN_QUOTE_CHARS:
                continue
            if needle not in haystack:
                speaker = utt.get("speaker", "?")
                warnings.append(
                    f"agenda[{i}].utterances[{j}] ({speaker}): "
                    f"quote not found verbatim in transcript: {text[:40]}..."
                )
    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_file", type=Path)
    parser.add_argument(
        "--part",
        choices=["full", "meta", "item", "synthesis"],
        default="full",
        help="which piece of the MeetingNote to validate (default: full)",
    )
    parser.add_argument(
        "--transcript",
        type=Path,
        help="original transcript; verify utterance quotes appear in it (full mode only)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat quote warnings as errors (exit 2)",
    )
    args = parser.parse_args()

    try:
        data = json.loads(args.json_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: {args.json_file}: invalid JSON: {e}")
        return 1

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    check(data, part_schema(schema, args.part), "$", errors)
    for err in errors:
        print(f"ERROR: {err}")
    if errors:
        print(f"{len(errors)} error(s)")
        return 1

    warnings: list[str] = []
    if args.transcript and args.part == "full":
        transcript = args.transcript.read_text(encoding="utf-8")
        warnings = check_quotes(data, transcript)
        for warn in warnings:
            print(f"WARN: {warn}")

    if warnings:
        print(f"OK with {len(warnings)} quote warning(s)")
        return 2 if args.strict else 0
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
