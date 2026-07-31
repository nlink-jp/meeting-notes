# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-07-31

### Added

- Initial release. Claude Code Skill successor to the
  [meeting-note](https://github.com/nlink-jp/meeting-note) CLI (v0.2.6),
  converted because single-shot LLM generation of the full record corrupted
  routinely on long meetings.
- Multi-pass workflow: outline → per-agenda-item extraction → meeting-level
  synthesis → deterministic assembly → verification → compilation. Each piece
  is validated on the spot and only broken pieces are re-extracted.
- `scripts/validate.py` — stdlib-only schema validation (full record or
  per-pass `--part meta|item|synthesis`) plus verbatim-quote verification
  against the original transcript (`--transcript`, warnings; `--strict`).
- `scripts/assemble.py` — deterministic merge of work files; derives
  `meeting_id` identically to the CLI, embeds `raw_transcript`, stamps
  `metadata`.
- `scripts/compile.py` — Markdown / self-contained HTML renderer ported from
  the CLI, without the Jinja2 dependency; adds `--lang en` label set
  (the CLI rendered Japanese labels only).
- JSON format unchanged from the CLI (`schema.json`,
  `references/data-format.md`); records produced by meeting-note v0.2.x
  validate and compile as-is (covered by a fixture round-trip test).
- Out of scope vs the CLI: audio input (transcribe first, e.g. with
  gem-transcribe) — and no GCP project, ADC, or GCS bucket required anymore.
