"""Prove the shipped demo inputs are complete, honestly labeled, and consistent.

This is the one command to run before a demo, and the one CI runs on every pull
request. Each fixture has its own unit test; this checks that the fixtures agree
with each other, which is where the failures that actually break a demo live.

    cd backend
    uv run python ../scripts/validate_fixtures.py
    uv run python ../scripts/validate_fixtures.py --strict

Exit codes:
    0  no errors. Warnings may still be reported.
    1  at least one error, or with --strict, at least one warning.
    2  a fixture could not be loaded at all.
"""

from __future__ import annotations

import argparse
import sys

from reefcommand.data.validation import (
    CHECKS,
    Finding,
    errors,
    load_inputs,
    run_all_checks,
    warnings,
)


def _summarise(inputs_description: str, findings: list[Finding], strict: bool) -> int:
    failed = errors(findings)
    warned = warnings(findings)

    print(inputs_description)
    print()

    if findings:
        print("Findings:")
        for finding in findings:
            print(finding.render())
        print()
    else:
        print("No findings.")
        print()

    print(f"{len(CHECKS)} checks run. {len(failed)} error(s), {len(warned)} warning(s).")

    if failed:
        print("\nFAILED. The demo inputs are not usable as they stand.")
        return 1
    if warned and strict:
        print("\nFAILED under --strict. Warnings are treated as errors.")
        return 1
    if warned:
        print(
            "\nPASSED with warnings. Nothing is broken, but the warnings above describe "
            "inputs the demo cannot use. Resolve them, then run with --strict."
        )
        return 0
    print("\nPASSED. The demo inputs are complete, honestly labeled, and consistent.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors. Use once the team has resolved them.",
    )
    args = parser.parse_args()

    try:
        inputs = load_inputs()
    except Exception as exc:  # report the file, do not swallow it
        print(f"A fixture could not be loaded: {exc}", file=sys.stderr)
        return 2

    description = (
        f"Loaded {len(inputs.sites)} sites, {len(inputs.scenarios)} resource scenarios, "
        f"{len(inputs.catalog)} catalog actions, {len(inputs.reports)} demo reports, "
        f"{len(inputs.updates)} follow-up report(s), "
        f"{len(inputs.structured)} structured observations."
    )
    return _summarise(description, run_all_checks(inputs), strict=args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
