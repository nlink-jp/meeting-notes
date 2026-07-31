# CLAUDE.md — meeting-notes

**Organization rules (mandatory): https://github.com/nlink-jp/.github/blob/main/CONVENTIONS.md**

See [`AGENTS.md`](AGENTS.md) for commands, structure, and gotchas.

## Non-negotiable rules

- **Docs in sync** — update `README.md` and `README.ja.md` in the same commit as behaviour changes.
- **Small, typed commits** — `feat:`, `fix:`, `docs:`, `test:`, `chore:`
- **`make check` before committing** — structural validation + script tests are this repo's test suite.
- **The `meeting-notes/` subdirectory is the distribution boundary** — only
  skill content goes inside it; `make package` ships exactly that directory
  (ADR-004).
- **Bundled scripts are stdlib-only Python** — no third-party dependencies,
  ever; they must run on any host the skill is installed on.

## Communication Language

All communication between contributors and Claude Code is conducted in **Japanese**.
