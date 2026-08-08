# meeting-notes

Claude Code Skill that structures a meeting transcript (TXT / VTT / SRT) into
a validated 3-layer JSON record — raw utterances, structured decisions with
rationale, and summaries — then compiles Markdown or self-contained HTML
minutes. Invoked as `/meeting-notes <transcript-file>`.

Successor to the archived [meeting-note](https://github.com/nlink-jp/meeting-note)
CLI. The CLI generated the entire JSON in a single LLM call, which corrupted
routinely on long meetings (the verbatim-quote layer makes the output as long
as the input). This skill extracts small pieces, validates each piece with a
bundled script, retries only what broke, and verifies every quote against the
original transcript — the agentic loop does what the CLI's repair code
approximated. The JSON format is unchanged; existing records still compile.

## Install

Download `meeting-notes-vX.Y.Z.zip` from
[Releases](https://github.com/nlink-jp/meeting-notes/releases), then register it:

- **In the app** (Claude Desktop, claude.ai, mobile) — add the zip from the
  skill settings (Customize → Skills). Prefer this route; it survives changes
  to where skills are stored on disk.
- **Claude Code** — `unzip meeting-notes-vX.Y.Z.zip -d ~/.claude/skills/`, or into a
  project's `.claude/skills/` for a project-scoped install.

From a checkout:

```bash
make install
```

That builds the release zip and unpacks *that*, so what you run is what a
release ships — a packaging defect breaks your install rather than reaching
users. `make install DEST=/path/to/skills` installs elsewhere;
`make uninstall` removes it.

Requirements: Claude Code, and `python3` (3.9+, stdlib only) for the bundled
validation/compile scripts.

## Usage

```
/meeting-notes path/to/transcript.vtt
/meeting-notes minutes.txt --lang en
/meeting-notes standup.srt --html
```

Produces next to the input, after a multi-pass extract → validate → verify
workflow:

- `<name>.json` — structured MeetingNote record (schema: `meeting-notes/schema.json`,
  semantics: `meeting-notes/references/data-format.md`)
- `<name>.md` — minutes (or `<name>.html`, self-contained, with `--html`)

Audio input is out of scope — transcribe first (e.g. with
[gem-transcribe](https://github.com/nlink-jp/gem-transcribe)), then run this
skill on the transcript.

Records from the predecessor CLI can be re-compiled directly:

```bash
python3 ~/.claude/skills/meeting-notes/scripts/compile.py meeting.json -o meeting.md
python3 ~/.claude/skills/meeting-notes/scripts/compile.py meeting.json -f html -o meeting.html --lang en
```

## Development

| Command | Purpose |
|---------|---------|
| `make check` (= `make test`) | Structural validation + script behaviour tests |
| `make install` | Copy the skill to `~/.claude/skills/meeting-notes` |
| `make package` | Build `dist/meeting-notes-vX.Y.Z.zip` (zip root = skill folder) |

## Documentation

- [Data Format Specification](meeting-notes/references/data-format.md)
- [RFP / design document](docs/en/meeting-notes-rfp.md)
- [日本語ドキュメント](README.ja.md)

## License

MIT
