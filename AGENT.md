# AGENT.md

Working rules for any AI agent operating in this repository.
These rules apply to all work in this project unless a human explicitly overrides them for a specific task.

## Project

ReefCommand is an AI decision-support system that turns environmental monitoring, field observations, scientific intervention guidance, and limited conservation resources into continuously updated reef-response plans.
It is a prototype whose goal is one reliable closed loop: observe, structure, investigate, fuse evidence, constrain to policy-eligible actions, reason about uncertainty, optimize, display plan, re-plan on new information.
A human reef manager approves all operational actions.
The system prioritizes, explains, surfaces uncertainty, requests more evidence, optimizes resources, and shows trade-offs.
It does not claim final scientific or operational authority.

## Writing style

Never use the em dash character.
Use a plain dash "-" instead.
This applies to code, comments, commit messages, documentation, dashboard copy, and any other text produced in this project.

When writing or substantially editing long Markdown files, put each full sentence on its own line.
Preserve normal Markdown structure such as headings, lists, code fences, and tables.
Avoid wrapping multiple sentences onto one physical line, because it makes diffs noisy and review harder.

## Version control

When writing commit messages, never auto-add your agent name as co-author.
Do not add Co-Authored-By trailers, "Generated with" footers, or any other attribution to an AI agent.
Write the commit message as the human author would write it: what changed and why.

Never manually modify CHANGELOG.md files.
Never manually modify any file marked as auto-generated.
If such a file needs to change, change its generator or its source of truth and regenerate it.

## Technical decisions

When making technical decisions, do not give much weight to development cost.
Prefer quality, simplicity, robustness, scalability, and long term maintainability.
A solution that takes longer to build but stays correct and understandable as the system grows is the right choice.
Avoid shortcuts that trade a lasting structural problem for a short term saving.

Keep the deterministic and non-deterministic parts of the system clearly separated.
Deterministic components stay deterministic: thermal evidence, evidence fusion, the intervention policy engine, and the optimizer.
The Coordinator is the only autonomous reasoning component, and its output must pass schema validation and business-rule validation before anything downstream consumes it.
Never let free-form model prose reach the optimizer.

## Bug fixes

When doing bug fixes, always start by reproducing the bug in an end-to-end setting as closely aligned with how an end user actually hits it as possible.
Drive it through the real entry point: the real UI, the real API call, the real data path, the real configuration.
Do not start from a narrow unit test that assumes where the problem is, because that tends to confirm a guess rather than find the cause.

Only after the bug reproduces end to end should you narrow down to the failing component.
Once fixed, verify the fix in the same end-to-end setting that reproduced it, then add the appropriate regression test at the tightest level that still covers the real failure.
This makes sure you find the real problem so your fix will actually solve it.

## End-to-end testing and UI quality

When end-to-end testing a product, be picky about the UI you see and be obsessed with pixel perfection.
Check alignment, spacing, typography, contrast, focus states, loading states, empty states, error states, and responsive behavior.
If something clearly looks off, even if it is not directly related to what you are doing, try to get it fixed along the way.
If it is too large to fix in the current change, report it clearly rather than silently ignoring it.

## Engineering excellence

Apply that same high standard to engineering excellence: lint, test failures, and test flakiness.
If you see one, even if it is not caused by what you are working on right now, still get it fixed.
A flaky test is a real defect, not background noise.
Do not disable, skip, or retry-loop a failing or flaky test to make a build green.
Fix the underlying cause, or escalate it explicitly with what you found.

## Data honesty

Never present simulated or synthetic data as real.
Simulated fleet, personnel, inventory, and budget data must be clearly labeled as simulated wherever it is displayed.
Synthetic rainfall, storm, or vessel signals must be clearly labeled as synthetic.
Log and display whether a value came from a live external call or from a cached snapshot.

Do not overstate what a number proves.
Evidence support scores are support scores, not probabilities, unless a probabilistic model has actually been calibrated against expert-labeled cases.
Prototype weights are stated assumptions, not scientific claims, and must be labeled as such.
