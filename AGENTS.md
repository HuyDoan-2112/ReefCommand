# AGENTS.md

General working rules for anyone contributing to this repository, human or AI.

This is a hackathon project with multiple contributors working in parallel.
These rules exist so that three people and their assistants produce one coherent codebase instead of three overlapping ones.

Project context lives in `CLAUDE.md`.
Read that first if you do not know what ReefCommand is.
Detailed rules live in `.agents/rules/`.

## Reading order

1. `CLAUDE.md` for what the project is and why it is built this way
2. This file for the general rules
3. `.agents/rules/` for the specific rule set relevant to your change
4. `.agents/teammates/<track>.md` for what your track owns

## The rules, in short

### Writing style

Never use the em dash character.
Use a plain dash `-` instead.
This applies to code, comments, commit messages, documentation, dashboard copy, and anything else produced here.
CI fails the build on any em dash or en dash in the tree.

When writing or substantially editing long Markdown files, put each full sentence on its own line.
Preserve normal Markdown structure such as headings, lists, code fences, and tables.
Avoid wrapping multiple sentences onto one physical line, because it makes diffs noisy and review harder.

### Version control

See `.agents/rules/commit-rules.md`.

Never auto-add your agent name as co-author.
No `Co-Authored-By` trailers, no "Generated with" footers, no AI attribution of any kind.
CI fails any PR whose commits contain one.

Never manually modify `CHANGELOG.md` or any file marked auto-generated.
Change the generator or the source of truth and regenerate.

### Technical decisions

See `.agents/rules/code-rules.md`.

Do not give much weight to development cost.
Prefer quality, simplicity, robustness, scalability, and long term maintainability.
A solution that takes longer to build but stays correct and understandable as the system grows is the right choice.
Avoid shortcuts that trade a lasting structural problem for a short term saving.

### Multi-agent and multi-contributor work

See `.agents/rules/multi-agent-rules.md`.

Stay inside your track.
Changes to shared contracts are a deliberate, reviewed act, never a side effect of feature work.

### Bug fixes

Always start by reproducing the bug end to end, as closely aligned with how an end user actually hits it as possible.
Drive it through the real entry point: the real UI, the real API call, the real data path, the real configuration.
Do not start from a narrow unit test that assumes where the problem is, because that tends to confirm a guess rather than find the cause.

Only after it reproduces end to end should you narrow down to the failing component.
Once fixed, verify in the same end-to-end setting that reproduced it, then add a regression test at the tightest level that still covers the real failure.
This makes sure you find the real problem so your fix actually solves it.

### End-to-end testing and UI quality

When end-to-end testing a product, be picky about the UI you see and be obsessed with pixel perfection.
Check alignment, spacing, typography, contrast, focus states, loading states, empty states, error states, and responsive behavior.
If something clearly looks off, even if it is not directly related to what you are doing, try to get it fixed along the way.
If it is too large to fix in the current change, report it clearly rather than silently ignoring it.

### Engineering excellence

Apply that same high standard to lint, test failures, and test flakiness.
If you see one, even if it is not caused by what you are working on right now, still get it fixed.
A flaky test is a real defect, not background noise.
Do not disable, skip, or retry-loop a failing or flaky test to make a build green.
Fix the underlying cause, or escalate it explicitly with what you found.

### Data honesty

Never present simulated or synthetic data as real.
Simulated fleet, personnel, inventory, and budget data must be clearly labeled as simulated wherever displayed.
Synthetic rainfall, storm, or vessel signals must be clearly labeled as synthetic.
Log and display whether a value came from a live external call or a cached snapshot.

Do not overstate what a number proves.
Evidence support scores are support scores, not probabilities, unless a probabilistic model has actually been calibrated against expert-labeled cases.
Prototype weights are stated assumptions, not scientific claims, and must be labeled as such.

## If a rule blocks you

Say so in the pull request.
Do not quietly work around it, and do not delete it.
A rule that turns out to be wrong should be changed in the open, in its own commit, with the reasoning written down.