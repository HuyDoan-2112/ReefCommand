"""DATA-08: the shipped demo inputs must be complete, honest, and consistent.

Two halves. The first asserts the real fixtures are clean. The second breaks a
copy of them on purpose, because a check that has never been seen to fail is not
evidence of anything.

    uv run pytest tests/unit/test_fixture_validation.py -q
"""

from __future__ import annotations

import pytest

from reefcommand.data import validation
from reefcommand.data.validation import Inputs, Severity
from reefcommand.domain.enums import Provenance


@pytest.fixture(scope="module")
def inputs() -> Inputs:
    return validation.load_inputs()


def _checks(findings, name):
    return [finding for finding in findings if finding.check == name]


# --- the shipped inputs -------------------------------------------------------


def test_every_fixture_loads(inputs) -> None:
    """If this raises, no other check in the suite means anything."""
    assert inputs.sites
    assert inputs.scenarios
    assert inputs.catalog
    assert inputs.reports
    assert inputs.structured


def test_shipped_inputs_have_no_errors(inputs) -> None:
    """The bar for merging. Warnings are allowed and reported; errors are not."""
    failures = validation.errors(validation.run_all_checks(inputs))
    assert not failures, "\n".join(finding.render() for finding in failures)


def test_findings_are_ordered_errors_first(inputs) -> None:
    severities = [finding.severity for finding in validation.run_all_checks(inputs)]
    assert severities == sorted(severities, key=lambda s: s is not Severity.ERROR)


# --- negative controls --------------------------------------------------------


def test_a_missing_site_is_caught(inputs) -> None:
    broken = inputs.model_copy(update={"sites": inputs.sites[1:]})
    findings = validation.check_study_area_is_complete(broken)
    assert findings
    assert all(f.severity is Severity.ERROR for f in findings)


def test_a_site_claiming_live_provenance_is_caught(inputs) -> None:
    site_id, provenances = next(iter(inputs.site_provenance.items()))
    lying = provenances[0].model_copy(update={"kind": Provenance.LIVE})
    broken = inputs.model_copy(
        update={"site_provenance": {**inputs.site_provenance, site_id: [lying, *provenances[1:]]}}
    )
    findings = validation.check_nothing_persisted_claims_to_be_live(broken)
    assert any("live" in finding.message for finding in findings)


def test_a_fixture_envelope_claiming_live_provenance_is_caught(inputs) -> None:
    lying = inputs.fixture_provenance[0].model_copy(update={"kind": Provenance.LIVE})
    broken = inputs.model_copy(
        update={"fixture_provenance": [lying, *inputs.fixture_provenance[1:]]}
    )
    findings = validation.check_nothing_persisted_claims_to_be_live(broken)
    assert any("envelope" in finding.message for finding in findings)


def test_a_report_pointing_at_an_unknown_site_is_caught(inputs) -> None:
    stray = inputs.reports[0].model_copy(update={"site_id": "atlantis"})
    broken = inputs.model_copy(update={"reports": [stray, *inputs.reports[1:]]})
    findings = validation.check_references_resolve(broken)
    assert any("atlantis" in finding.message for finding in findings)


def test_a_report_with_no_structuring_fixture_is_caught(inputs) -> None:
    """This is the failure that would make the OBSERVE to STRUCTURE step raise."""
    broken = inputs.model_copy(update={"structured": inputs.structured[1:]})
    findings = validation.check_references_resolve(broken)
    assert any("no structuring fixture" in finding.message for finding in findings)


def test_a_structured_observation_disagreeing_about_its_site_is_caught(inputs) -> None:
    other_site = next(
        site.site_id for site in inputs.sites if site.site_id != inputs.structured[0].site_id
    )
    moved = inputs.structured[0].model_copy(update={"site_id": other_site})
    broken = inputs.model_copy(update={"structured": [moved, *inputs.structured[1:]]})
    findings = validation.check_references_resolve(broken)
    assert any("but its report says" in finding.message for finding in findings)


def test_a_placeholder_citation_is_caught(inputs) -> None:
    uncited = inputs.catalog[0].model_copy(update={"provenance": "TODO: cite something"})
    broken = inputs.model_copy(update={"catalog": [uncited, *inputs.catalog[1:]]})
    findings = validation.check_every_catalog_action_is_cited(broken)
    assert any("placeholder" in finding.message for finding in findings)


def test_a_citation_with_no_url_is_caught(inputs) -> None:
    vague = inputs.catalog[0].model_copy(update={"provenance": "Somebody said so once"})
    broken = inputs.model_copy(update={"catalog": [vague, *inputs.catalog[1:]]})
    findings = validation.check_every_catalog_action_is_cited(broken)
    assert any("retrievable" in finding.message for finding in findings)


def test_a_coordinate_outside_the_keys_is_caught(inputs) -> None:
    """A transcription error here silently selects the wrong satellite pixel."""
    site = inputs.sites[0]
    moved = site.model_copy(
        update={"location": site.location.model_copy(update={"latitude": 41.9})}
    )
    broken = inputs.model_copy(update={"sites": [moved, *inputs.sites[1:]]})
    findings = validation.check_coordinates_are_in_the_keys(broken)
    assert any("outside the Florida Keys" in finding.message for finding in findings)


def test_a_cause_with_no_action_is_caught(inputs) -> None:
    disease_free = [
        action
        for action in inputs.catalog
        if not any(cause.value == "disease" for cause in action.applicable_causes)
    ]
    broken = inputs.model_copy(update={"catalog": disease_free})
    findings = validation.check_every_cause_has_an_action(broken)
    assert any("disease" in finding.message for finding in findings)


def test_an_action_no_scenario_can_execute_is_caught(inputs) -> None:
    """The check that found the real one. An action nobody can run is invisible."""
    action = inputs.catalog[0]
    impossible = action.model_copy(
        update={"resources": action.resources.model_copy(update={"dive_hours": 999.0})}
    )
    broken = inputs.model_copy(update={"catalog": [impossible, *inputs.catalog[1:]]})
    findings = _checks(validation.check_actions_are_executable(broken), "feasibility")
    assert any("cannot be executed under any shipped scenario" in f.message for f in findings)


def test_an_action_that_only_one_scenario_can_run_is_not_flagged(inputs) -> None:
    """Feasible somewhere is feasible. Only universally impossible actions are flagged."""
    action = next(a for a in inputs.catalog if a.resources.boats <= 1)
    two_boats = action.model_copy(
        update={"resources": action.resources.model_copy(update={"boats": 2})}
    )
    partly = inputs.model_copy(update={"catalog": [two_boats]})
    findings = validation.check_actions_are_executable(partly)
    assert not [f for f in findings if "cannot be executed" in f.message]


def test_shipped_inputs_have_no_warnings(inputs) -> None:
    assert not validation.warnings(validation.run_all_checks(inputs))
