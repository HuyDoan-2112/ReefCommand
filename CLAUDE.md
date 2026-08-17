# CLAUDE.md

This project keeps a single source of truth for agent working rules.
Read and follow it before doing any work here.

@AGENT.md

## Quick reminders

These are the rules most often broken, restated for emphasis.
The full text and rationale live in AGENT.md.

- Never use the em dash character. Use a plain dash "-" instead.
- Never add yourself as co-author or add any AI attribution to commit messages.
- Never hand-edit CHANGELOG.md or any auto-generated file. Change the generator or the source of truth instead.
- In long Markdown files, put each full sentence on its own line.
- Prefer quality, simplicity, robustness, scalability, and long term maintainability over development cost.
- Reproduce every bug end to end, the way a real user hits it, before fixing it.
- Be picky about UI. If something looks off, get it fixed even if it is unrelated to the current task.
- Fix lint errors, failing tests, and flaky tests when you see them, regardless of who caused them.
