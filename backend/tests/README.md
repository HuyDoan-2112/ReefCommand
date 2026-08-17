# Tests

Three levels, and the level matters.

| Directory | What it covers |
| --- | --- |
| `unit/` | One module in isolation. Threshold logic, scoring math, schema invariants. |
| `integration/` | Two or more stages wired together. Fusion into policy into Coordinator validation. |
| `e2e/` | The real entry point: HTTP in, plan out. |

## Fixing a bug

Start in `e2e/`.
Reproduce the bug through the path an end user actually takes: the real API call,
the real data path, the real configuration.
Only after it reproduces end to end should you narrow down to the failing module.

Starting from a narrow unit test assumes where the problem is, and tends to
confirm a guess rather than find the cause.

Once fixed, verify in the same end-to-end setting that reproduced it, then add the
regression test at the tightest level that still covers the real failure.

## Flakiness

A flaky test is a real defect, not background noise.
Do not disable, skip, or retry-loop a failing or flaky test to make a build green.
Fix the cause, or escalate it explicitly with what you found.
