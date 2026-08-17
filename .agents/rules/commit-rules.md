# Commit rules

Commits should be small, intentional, and easy to review.

## Before committing

- Read `CLAUDE.md`, `AGENTS.md`, and the relevant track brief.
- Inspect `git status` and keep unrelated changes out of the commit.
- Run the checks relevant to the files changed.
- Do not commit secrets, `.env` files, local caches, build output, or generated files.

## Commit messages

- Use an imperative subject, for example `Implement deterministic site scoring`.
- Keep the subject concise and focused on the user-visible or architectural change.
- Explain important trade-offs in the body when the subject is not enough.
- Never add `Co-Authored-By`, `Generated with`, AI attribution, or agent attribution.

## Scope and history

- Do not mix refactors, feature work, formatting churn, and unrelated fixes.
- Do not rewrite shared history or force-push unless the user explicitly asks.
- Never manually edit `CHANGELOG.md` or other generated files.
- Prefer a new commit that explains a correction over hiding changes in an existing commit.
