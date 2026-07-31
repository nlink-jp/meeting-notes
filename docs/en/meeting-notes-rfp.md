# RFP: meeting-notes

> Generated: 2026-07-31
> Status: Approved

## 1. Problem Statement

Turn a meeting transcript (TXT/VTT/SRT) into a reusable structured record —
three layers: verbatim utterances, decisions with rationale, summaries — and
compile human-readable minutes (Markdown/HTML). Target user: the nlink-jp
operator.

The predecessor, the meeting-note CLI (lab-series, Python + Vertex AI
Gemini), solved the same problem but **failed frequently at structured-data
generation**. The cause is inherent to its design: it generated the entire
JSON — including the verbatim-quote layer — in a single LLM call, so output
length scales with input length, and Gemini corrupts long JSON outputs at
high rates (including mid-stream corruption with finish_reason=STOP, a known
issue from gem-transcribe ADR-0001). jsonfix repairs syntax only and can
destroy semantics.

Converting to a Claude Code Skill addresses the root cause (fragility of
single-shot generation) with an agentic loop: split extraction → per-piece
validation → retry only what broke → verify quotes against the source.

## 2. Functional Specification

### Commands / API Surface

- `/meeting-notes <transcript-file> [--lang ja|en] [--html]`
- Bundled scripts (driven by the skill workflow; usable standalone):
  - `scripts/validate.py <json> [--part meta|item|synthesis] [--transcript <file>] [--strict]`
  - `scripts/assemble.py --meta ... --synthesis ... --items ... --transcript ... -o <json> --model <id>`
  - `scripts/compile.py <json> [-f markdown|html] [-o out] [--lang ja|en] [--tz <tz>]`

### Input / Output

- Input: transcript file (.txt / .vtt / .srt / exported JSON)
- Output: `<name>.json` (MeetingNote record, conforming to `schema.json`)
  plus `<name>.md` or self-contained `<name>.html`
- The JSON format is fully compatible with meeting-note CLI v0.2.x
  (old records validate and compile as-is)

### Configuration

None. All of the CLI's configuration (GCP project / location / model / GCS
bucket / ADC) disappears. Output language is auto-detected (CJK → ja) with a
`--lang` override.

### External Dependencies

- Claude Code (skill host)
- python3 3.9+ for the bundled scripts — **standard library only**

## 3. Design Decisions

- **The multi-pass pipeline is spelled out in SKILL.md**: outline →
  per-agenda-item extraction → meeting-level synthesis → deterministic
  assembly → verification → compilation. "Never write the whole record in
  one go" is the skill's reason to exist, so SKILL.md forbids optimizing the
  passes away.
- **Deterministic work stays in scripts**: validation, assembly, and
  rendering are never done by the LLM. `meeting_id` derivation matches the
  CLI (SHA-256(`title:date`)[:12]) for compatibility.
- **Quotes are verified against the source**: `utterances[].text` must be
  verbatim copies; validate.py checks them as whitespace-normalized substring
  matches (warning-based) — a defense against LLM quote drift.
- **Scripts are stdlib-only**: pydantic / Jinja2 / jsonschema dropped; the
  HTML template is ported to a Python string.
- **compile supports ja and en** (the CLI rendered Japanese labels only).
- **Prompt-injection defense sits at the top of SKILL.md**: the transcript is
  data, never instructions; anomalies are surfaced in the final report.
- **Audio is out of scope**: Claude cannot process audio directly; recordings
  are transcribed upstream (e.g. gem-transcribe) — the skill only points
  there.
- Complements: downstream of gem-transcribe (audio → transcript); combined
  with lite-rag it substitutes for the CLI's cancelled Phase 2 (search),
  unchanged from before.

### Explicitly out of scope

- Audio input (the CLI's `-a`)
- SQLite / embeddings / search (same as the CLI's cancelled Phase 2)
- Any external LLM API calls (Gemini etc.)

## 4. Development Plan

### Phase 1: Core

SKILL.md (multi-pass workflow) + schema.json + validate/assemble/compile
scripts + a unittest suite, including a compatibility round-trip pinned to
real output of the predecessor CLI as a fixture.

### Phase 2: Features

Awaiting real-world feedback. Candidates: VTT speaker-label normalization
help, stronger outline-splitting guidance for 2h+ meetings.

### Phase 3: Release

v0.1.0 — publish the GitHub repository, attach the `make package` zip as a
Release asset, add the submodule to the skills-series umbrella, update the
org profile / nlink-web-site catalogs, and archive the old meeting-note
repository (after adding a successor pointer to its README).

## 5. Required API Scopes / Permissions

None. (The Vertex AI / GCS IAM the CLI required is no longer needed.)

## 6. Series Placement

Series: skills-series
Reason: it is a Claude Code Skill, following the one-repository-per-skill
structure (ADR-004). The lab-series predecessor is archived.

## 7. External Platform Constraints

- Claude Code Skills constraints: directory name = slash command =
  frontmatter name; the distribution zip has the skill folder at its root
  (the layout claude.ai accepts).
- The script runtime is not guaranteed, hence stdlib-only.
- No network access at all, so the skill also works in claude.ai sandboxes.

---

## Discussion Log

- Starting point: "what meeting-note does in code should be achievable with
  Skills today." Of the 1260 lines, only the prompt and the schema are
  essential; most of the rest (Gemini client, config resolution, jsonfix,
  type-coercion validators) exists to babysit the API.
- Motivation sharpened: frequent failures when structuring from VTT/audio.
  Diagnosis: single-shot generation of a huge JSON containing the verbatim
  layer — operating exactly where Gemini demonstrably corrupts output. The
  gem-transcribe ADR-0001 lessons (per-item salvage, no all-at-once
  validation) had not been applied to meeting-note.
- Alternatives: (A) keep the CLI, split the pipeline — reliable but more
  code; (B) convert to a Skill — the agentic loop natively does the
  splitting, retrying, and quote recovery. Chose B given interactive usage
  patterns and escaping the Gemini 3 migration.
- Naming: `meeting-note` already exists on GitHub, so `meeting-notes` (user's
  choice). The old repository will be archived. Audio delegation to
  gem-transcribe was considered but cut to keep v0.1.0 thin (user's call).
