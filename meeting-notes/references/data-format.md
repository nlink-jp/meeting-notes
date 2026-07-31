# Data Format Specification

This document defines the structured JSON produced by the meeting-notes skill
and consumed by `scripts/compile.py`. The machine-checkable subset lives in
[`../schema.json`](../schema.json); this document explains the semantics.

## Overview

The MeetingNote JSON is designed to be a **self-contained, reusable data
source**. It captures not just what was discussed, but *why* decisions were
made, *who* influenced them, and *what* the original speakers actually said.

```
MeetingNote
├── Meeting identification (id, title, date, type, context)
├── Participants[] (name, role, affiliation)
├── ParticipantDynamics[] (from → to, relation type)
├── Agenda[]
│   ├── Status (decided / pending / rejected / informational)
│   ├── Utterances[] (speaker, verbatim text)  ← raw evidence
│   ├── Discussion points[]                     ← summarized
│   ├── Decisions[] (what, WHY, alternatives)   ← structured
│   ├── ActionItems[] (owner, task, due)
│   └── Unresolved[] (issue, blocker)
├── Key takeaways[]
├── raw_transcript                              ← full original text
└── Metadata (source, generator, model)
```

## Root: MeetingNote

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `meeting_id` | string | auto | Unique ID. Derived as SHA-256(`title:date`)[:12] by `assemble.py` if empty |
| `title` | string | yes | Meeting title |
| `date` | ISO 8601 datetime | yes | Meeting start date/time |
| `duration_seconds` | integer | no | Duration in seconds |
| `meeting_type` | enum | no | `regular` / `ad_hoc` / `review` / `decision` / `informational` |
| `context` | string | no | Project or background this meeting relates to |
| `participants` | Participant[] | yes | List of attendees |
| `participant_dynamics` | ParticipantDynamics[] | no | Directional relationships between participants |
| `agenda` | AgendaItem[] | yes | Topics discussed |
| `key_takeaways` | string[] | no | 3-5 meeting-level summary points |
| `raw_transcript` | string | no | Full original transcript text. Populated by `assemble.py` (never re-generated) to preserve source material |
| `metadata` | MeetingMetadata | yes | Generation metadata |

## Participant

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Speaker name |
| `role` | enum | no | `organizer` / `decision_maker` / `proposer` / `reporter` / `observer` |
| `affiliation` | string | no | Team, department, or title |

### Role definitions

| Value | Description |
|-------|-------------|
| `organizer` | Chairs the meeting, sets agenda, manages flow |
| `decision_maker` | Has authority to approve or reject proposals |
| `proposer` | Presents ideas, proposals, or alternatives |
| `reporter` | Provides status updates or factual information |
| `observer` | Listens without active contribution |

## ParticipantDynamics

Captures **directional** relationships observed during the meeting.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `from` | string | yes | Person initiating the interaction |
| `to` | string | yes | Person receiving the interaction |
| `relation` | enum | yes | Type of relationship (see below) |
| `topic` | string | no | Related agenda item title |
| `detail` | string | no | Specific description of the interaction |

### Relation types

| Value | Description | Example |
|-------|-------------|---------|
| `proposal_approval` | One proposes, another approves | "Suzuki proposed Option B, Sato approved" |
| `objection_reproposal` | One objects, leading to a revised proposal | "Tanaka objected to timeline, Suzuki revised" |
| `delegation` | One assigns work to another | "Manager delegated investigation to analyst" |
| `question_answer` | One asks, another answers | "Legal asked about data residency, Infra answered" |
| `report` | One reports status/findings to another | "SOC analyst reported incident timeline to CISO" |
| `instruction` | One gives directives to another | "Chair instructed to prepare cost comparison" |

## AgendaItem

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | yes | Topic title |
| `status` | enum | yes | `decided` / `pending` / `rejected` / `informational` |
| `summary` | string | no | Summary of the discussion |
| `speakers` | string[] | no | Names of people who spoke on this topic |
| `utterances` | Utterance[] | no | Raw speaker-attributed statements (see below) |
| `discussion_points` | string[] | no | Key points discussed (summarized) |
| `decisions` | Decision[] | no | Decisions made on this topic |
| `action_items` | ActionItem[] | no | Tasks assigned |
| `unresolved` | UnresolvedItem[] | no | Issues carried forward |

### Status definitions

| Value | Description |
|-------|-------------|
| `decided` | A conclusion was reached and agreed upon |
| `pending` | Discussion occurred but no conclusion; carried forward |
| `rejected` | A proposal was explicitly rejected |
| `informational` | Information sharing only; no decision required |

## Utterance

Preserves **raw speaker-attributed statements** relevant to each agenda item.
These serve as primary evidence even after the source files are deleted.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `speaker` | string | yes | Name of the person who spoke |
| `text` | string | yes | Verbatim text, copied from the transcript (checked by `validate.py --transcript`) |
| `timestamp` | string | no | Time within the meeting (if available from source) |

## Decision

The core differentiator of this format: decisions include **rationale**.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `what` | string | yes | What was decided |
| `why` | string | yes | **Why** this decision was made (rationale) |
| `alternatives_considered` | Alternative[] | no | Other options that were discussed |
| `decided_by` | string[] | no | Names of people who made or approved the decision |

### Alternative

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `option` | string | yes | The alternative that was considered |
| `rejected_because` | string | yes | Why it was rejected |

## ActionItem

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `owner` | string | yes | Person responsible |
| `task` | string | yes | Task description |
| `due` | string | no | Deadline (free text, e.g. "2026-04-17", "next Friday") |
| `context` | string | no | Which decision or discussion this originated from |

## UnresolvedItem

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `issue` | string | yes | What remains unresolved |
| `blocker` | string | no | What is preventing resolution |
| `carry_forward_to` | string | no | Where this will be addressed (e.g. "next meeting") |

## MeetingMetadata

Stamped by `scripts/assemble.py`, never produced by extraction.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_audio` | string | no | Always empty — audio input is out of scope (kept for compatibility with meeting-note CLI records) |
| `source_transcript` | string | no | Transcript filename, or "provided" |
| `generated_by` | string | yes | Generator (e.g. "meeting-notes (Claude Code skill)") |
| `generated_at` | ISO 8601 datetime | yes | Generation timestamp (UTC) |
| `model` | string | yes | Model that performed the extraction |

## Data layers

The JSON contains three layers of information at different abstraction levels:

| Layer | Fields | Purpose |
|-------|--------|---------|
| **Raw** | `raw_transcript`, `utterances[]` | Original source material. Preserved verbatim for archival and traceability |
| **Structured** | `decisions[]`, `action_items[]`, `unresolved[]`, `participant_dynamics[]` | Machine-queryable facts |
| **Summarized** | `summary`, `discussion_points[]`, `key_takeaways[]` | Human-readable condensation |

This layering ensures the JSON is useful both as a **database record**
(structured layer) and as a **source of truth** (raw layer) even after the
original files are deleted.

## Validation

`scripts/validate.py` enforces the format at two levels:

- **Schema**: types, required fields, and enums from `schema.json`, either on
  the full record or per work-file (`--part meta|item|synthesis`).
- **Quote fidelity**: with `--transcript`, every `utterances[].text` must
  appear in the original transcript (whitespace-insensitive substring match).
  Mismatches are warnings — the raw layer is only trustworthy if quotes are
  real, so the skill workflow requires re-checking each one against the
  source.

## Compatibility

The format is field-compatible with records produced by the archived
`meeting-note` CLI (v0.2.x). Existing records compile unchanged with
`scripts/compile.py`.
