# Code rules

Prefer correctness, clarity, and maintainability over the shortest implementation.

## Architecture

- Keep the deterministic and autonomous boundaries described in `CLAUDE.md` and `docs/architecture.md`.
- Keep shared contracts in `backend/src/reefcommand/domain/` stable and deliberate.
- The LLM must not invent interventions, allocate resources, or send free-form text to the optimizer.
- Preserve provenance for external, cached, simulated, and synthetic data all the way to the API and dashboard.
- Make invalid states fail loudly at the boundary where they are detected.

## Implementation

- Prefer small functions with explicit inputs and outputs.
- Add or update tests with behavior changes.
- Use type hints and the repository's configured lint and format tools.
- Do not silently replace real data with synthetic data or placeholders.
- Do not call support scores probabilities unless the model has been calibrated against labeled data.
- Do not add an LLM call where a documented deterministic rule is sufficient.

## Verification

- For a bug, reproduce it through the real API or UI path before narrowing to a unit test.
- Run the same end-to-end path after the fix.
- Treat lint failures, test failures, and flaky tests as defects to fix, not noise to suppress.
- Check loading, empty, error, responsive, contrast, and focus states for UI changes.
