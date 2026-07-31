# AGENTS.md — meeting-notes

## Project summary

Claude Code Skill that structures a meeting transcript (TXT/VTT/SRT) into a
validated 3-layer JSON record (raw utterances / structured decisions /
summaries) and compiles Markdown or self-contained HTML minutes. Invoked as
`/meeting-notes <transcript-file>`. Successor to the archived meeting-note
CLI; same JSON format, but extraction is multi-pass with per-piece validation
instead of one giant LLM call.

## Key commands

| Command | Purpose |
|---------|---------|
| `make check` (= `make test`) | Structural validation + script behaviour tests |
| `make install` | Copy the skill to `~/.claude/skills/meeting-notes` |
| `make install DEST=<path>` | Copy to a custom skills directory |
| `make uninstall` | Remove the installed copy |
| `make package` | Build `dist/meeting-notes-vX.Y.Z.zip` (zip root = skill folder) |
| `make clean` | Remove `dist/` |

## Directory structure

```
meeting-notes/
├── meeting-notes/           The skill — the only thing that ships
│   ├── SKILL.md             Frontmatter + multi-pass workflow instructions
│   ├── schema.json          MeetingNote JSON Schema (draft-07 subset)
│   ├── references/
│   │   └── data-format.md   Field semantics, 3-layer model
│   └── scripts/             stdlib-only Python (3.9+), no third-party deps
│       ├── validate.py      Schema validation + verbatim-quote check
│       ├── assemble.py      Deterministic merge of per-pass work files
│       └── compile.py       Markdown / self-contained HTML renderer (ja/en)
├── tests/
│   ├── validate-skill.sh    Frontmatter + link structure checks
│   ├── run-script-tests.py  unittest suite for the scripts
│   └── fixtures/            sample-meeting.{txt,json} — real output of the
│                            predecessor CLI (format-compatibility fixture)
├── docs/{ja,en}/            RFP / design document
├── Makefile
├── README.md / README.ja.md
├── CHANGELOG.md
├── CLAUDE.md / AGENTS.md
└── LICENSE
```

## Gotchas

- The `meeting-notes/` subdirectory is the distribution boundary (ADR-004):
  `make package` zips exactly that directory, so the zip root is the skill
  folder — the layout claude.ai accepts. Never add repo-level files inside
  it, and never bundle README.md into the zip.
- The directory name is the slash command; frontmatter `name` must match it.
  `make check` enforces this.
- **Scripts must stay stdlib-only** — they run wherever the skill is
  installed (Claude Code hosts, claude.ai sandboxes); a pip dependency would
  break them silently.
- `scripts/validate.py` is a deliberate subset of JSON Schema (type,
  required, properties, items, enum, format: date-time). If schema.json ever
  grows beyond that subset, extend the validator with it.
- The quote check normalizes whitespace only; a legitimately re-worded
  utterance shows as WARN. That is by design — the skill workflow requires
  re-checking each WARN against the source, and exit stays 0 (use `--strict`
  to make warnings fatal, e.g. in tests).
- `assemble.py` derives `meeting_id` as SHA-256(`title:date.isoformat()`)[:12]
  — identical to the predecessor CLI's pydantic validator. The round-trip
  test pins this; don't change the derivation.
- `tests/fixtures/` is real output of the archived meeting-note CLI. It is
  simulated meeting content (no real PII); keep it that way.
- After editing SKILL.md or scripts, run `make install` to refresh the
  deployed copy.
- Releases follow the org checklist with `make package` in place of a binary
  build; before uploading, unzip the artifact and confirm
  `meeting-notes/SKILL.md` sits directly under the zip root.

## Module path

Repository: `github.com/nlink-jp/meeting-notes`
