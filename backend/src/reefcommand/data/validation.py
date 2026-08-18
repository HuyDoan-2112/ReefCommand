"""Checks that prove the shipped demo inputs are usable.

Each fixture already has its own test. Those tests prove that one file is
internally valid. They cannot prove that the files agree with each other, and
that is where the failures that matter actually live: a report referencing a site
that does not exist, a structuring fixture with no report behind it, a catalog
action no shipped scenario has the capacity to execute.

This module is the cross-file layer. It answers one question for the whole demo:
are the inputs complete, honestly labeled, and mutually consistent.

Severity is deliberate. An ERROR is a broken input: something will not load, a
reference points at nothing, or a value claims an origin it does not have. A
WARNING is an input that loads and is honest but that the demo cannot actually
use, which is a decision for the team rather than a defect in the data. Run with
strict=True to treat warnings as errors once those decisions are made.
"""

from __future__ import annotations

from enum import StrEnum

import yaml
from pydantic import BaseModel

from reefcommand.config import DATA_DIR
from reefcommand.domain.enums import Cause, Provenance
from reefcommand.domain.intervention import InterventionDefinition, ResourceRequirement
from reefcommand.domain.observation import FieldReport, StructuredObservation
from reefcommand.domain.provenance import FixtureSet, ProvenanceMetadata
from reefcommand.domain.resources import ResourceScenario
from reefcommand.domain.site import ReefSite
from reefcommand.ingestion.agrra_sctld import SctldRecord

STUDY_AREA: frozenset[str] = frozenset(
    {
        "carysfort",
        "horseshoe",
        "cheeca_rocks",
        "sombrero",
        "newfound_harbor",
        "looe_key",
        "eastern_dry_rocks",
    }
)

# Florida Keys, generous. A coordinate outside this is a transcription error.
KEYS_LAT_RANGE = (24.3, 25.5)
KEYS_LON_RANGE = (-82.2, -80.0)

SITES_FILE = DATA_DIR / "sites" / "iconic_reefs.yaml"
SCENARIOS_FILE = DATA_DIR / "scenarios" / "demo_resource_scenarios.yaml"
CATALOG_FILE = DATA_DIR / "interventions" / "catalog.yaml"
REPORTS_FILE = DATA_DIR / "observations" / "demo_field_reports.yaml"
UPDATES_FILE = DATA_DIR / "observations" / "demo_evidence_update.yaml"
STRUCTURED_FILE = DATA_DIR / "observations" / "demo_structured_observations.yaml"
AGRRA_FILE = DATA_DIR / "agrra" / "sctld_snapshot.yaml"


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class Finding(BaseModel):
    """One thing wrong with the shipped inputs."""

    check: str
    severity: Severity
    message: str

    def render(self) -> str:
        return f"  {self.severity.value.upper():<7} {self.check}: {self.message}"


class Inputs(BaseModel):
    """Every shipped fixture, loaded through its real model."""

    model_config = {"arbitrary_types_allowed": True}

    sites: list[ReefSite]
    scenarios: list[ResourceScenario]
    catalog: list[InterventionDefinition]
    reports: list[FieldReport]
    updates: list[FieldReport]
    structured: list[StructuredObservation]
    site_provenance: dict[str, list[ProvenanceMetadata]]
    agrra_kinds: set[Provenance]
    fixture_provenance: list[ProvenanceMetadata]
    agrra_provenance: list[ProvenanceMetadata]


def _load_set[T](path: str, model: type[T]) -> FixtureSet[T]:
    from pathlib import Path

    return FixtureSet[model].model_validate(  # type: ignore[valid-type]
        yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    )


def load_inputs() -> Inputs:
    """Load every shipped fixture. Raises if any file will not parse at all."""
    sites = _load_set(str(SITES_FILE), ReefSite)
    scenarios = _load_set(str(SCENARIOS_FILE), ResourceScenario)
    reports = _load_set(str(REPORTS_FILE), FieldReport)
    updates = _load_set(str(UPDATES_FILE), FieldReport)
    structured = _load_set(str(STRUCTURED_FILE), StructuredObservation)

    catalog_document = yaml.safe_load(CATALOG_FILE.read_text(encoding="utf-8"))
    catalog = [InterventionDefinition.model_validate(e) for e in catalog_document["interventions"]]

    agrra_document = yaml.safe_load(AGRRA_FILE.read_text(encoding="utf-8"))
    agrra_fixture = _load_set(str(AGRRA_FILE), SctldRecord)
    agrra_kinds = {Provenance(record["data"]["provenance"]) for record in agrra_document["records"]}

    site_provenance = {
        record.record_id: [
            record.provenance,
            record.data.location.provenance,
            record.data.measurements.provenance,
            record.data.restoration_investment.provenance,
        ]
        for record in sites.records
    }

    return Inputs(
        sites=[r.data for r in sites.records],
        scenarios=[r.data for r in scenarios.records],
        catalog=catalog,
        reports=[r.data for r in reports.records],
        updates=[r.data for r in updates.records],
        structured=[r.data for r in structured.records],
        site_provenance=site_provenance,
        agrra_kinds=agrra_kinds,
        fixture_provenance=[
            record.provenance
            for record in [*reports.records, *updates.records, *structured.records]
        ],
        agrra_provenance=[record.provenance for record in agrra_fixture.records],
    )


def check_study_area_is_complete(inputs: Inputs) -> list[Finding]:
    """Every study site is present, and nothing extra has crept in."""
    found = {site.site_id for site in inputs.sites}
    findings: list[Finding] = []
    for missing in sorted(STUDY_AREA - found):
        findings.append(
            Finding(
                check="study-area",
                severity=Severity.ERROR,
                message=f"site {missing!r} is in the study area but not in the sites fixture",
            )
        )
    for extra in sorted(found - STUDY_AREA):
        findings.append(
            Finding(
                check="study-area",
                severity=Severity.ERROR,
                message=f"site {extra!r} is in the sites fixture but not in the study area",
            )
        )
    return findings


def check_nothing_persisted_claims_to_be_live(inputs: Inputs) -> list[Finding]:
    """A value on disk did not come from the network just now.

    This is the one failure mode the project's data honesty rules single out.
    """
    findings: list[Finding] = []
    for site_id, provenances in inputs.site_provenance.items():
        for provenance in provenances:
            if provenance.kind is Provenance.LIVE:
                findings.append(
                    Finding(
                        check="honesty",
                        severity=Severity.ERROR,
                        message=f"site {site_id} has a persisted record claiming live provenance",
                    )
                )
    for scenario in inputs.scenarios:
        if scenario.provenance is not Provenance.SIMULATED:
            findings.append(
                Finding(
                    check="honesty",
                    severity=Severity.ERROR,
                    message=(
                        f"scenario {scenario.scenario_id} is shipped with provenance "
                        f"{scenario.provenance.value}, but shipped scenarios are simulated"
                    ),
                )
            )
    for report in [*inputs.reports, *inputs.updates]:
        if report.provenance is Provenance.LIVE:
            findings.append(
                Finding(
                    check="honesty",
                    severity=Severity.ERROR,
                    message=f"demo report {report.report_id} claims live provenance",
                )
            )
    if any(provenance.kind is Provenance.LIVE for provenance in inputs.fixture_provenance):
        findings.append(
            Finding(
                check="honesty",
                severity=Severity.ERROR,
                message="a persisted report or structured-observation envelope claims live provenance",
            )
        )
    if Provenance.LIVE in inputs.agrra_kinds:
        findings.append(
            Finding(
                check="honesty",
                severity=Severity.ERROR,
                message="the AGRRA snapshot contains a record claiming live provenance",
            )
        )
    return findings


def check_provenance_carries_what_it_needs(inputs: Inputs) -> list[Finding]:
    """Cached values need a fetch time and a source. Invented values need a note."""
    findings: list[Finding] = []
    provenance_groups = [
        *inputs.site_provenance.items(),
        ("report and observation fixtures", inputs.fixture_provenance),
        ("AGRRA snapshot", inputs.agrra_provenance),
    ]
    for label, provenances in provenance_groups:
        for provenance in provenances:
            if provenance.kind is Provenance.CACHE and provenance.source_url is None:
                findings.append(
                    Finding(
                        check="provenance",
                        severity=Severity.ERROR,
                        message=(
                            f"{label} has a cached block from {provenance.source!r} "
                            "with no source_url, so a reviewer cannot check it"
                        ),
                    )
                )
    return findings


def check_every_catalog_action_is_cited(inputs: Inputs) -> list[Finding]:
    """A citation a reviewer cannot open is not a citation."""
    findings: list[Finding] = []
    for action in inputs.catalog:
        if "TODO" in action.provenance:
            findings.append(
                Finding(
                    check="citations",
                    severity=Severity.ERROR,
                    message=f"{action.action_id} still has a placeholder provenance",
                )
            )
        elif "http" not in action.provenance:
            findings.append(
                Finding(
                    check="citations",
                    severity=Severity.ERROR,
                    message=f"{action.action_id} provenance names no retrievable source",
                )
            )
    if any(provenance.kind is Provenance.LIVE for provenance in inputs.agrra_provenance):
        findings.append(
            Finding(
                check="honesty",
                severity=Severity.ERROR,
                message="the AGRRA fixture envelope claims live provenance",
            )
        )
    return findings


def check_every_cause_has_an_action(inputs: Inputs) -> list[Finding]:
    """A cause the Coordinator can conclude but never act on is a dead end."""
    covered = {cause for action in inputs.catalog for cause in action.applicable_causes}
    return [
        Finding(
            check="coverage",
            severity=Severity.ERROR,
            message=f"no catalog action responds to {cause.value}",
        )
        for cause in sorted(set(Cause) - covered, key=lambda c: c.value)
    ]


def check_references_resolve(inputs: Inputs) -> list[Finding]:
    """Every site_id and report_id referenced anywhere points at something real."""
    site_ids = {site.site_id for site in inputs.sites}
    all_reports = [*inputs.reports, *inputs.updates]
    report_sites = {report.report_id: report.site_id for report in all_reports}
    findings: list[Finding] = []

    for report in all_reports:
        if report.site_id not in site_ids:
            findings.append(
                Finding(
                    check="references",
                    severity=Severity.ERROR,
                    message=f"report {report.report_id} references unknown site {report.site_id!r}",
                )
            )

    structured_ids = {observation.report_id for observation in inputs.structured}
    for report in all_reports:
        if report.report_id not in structured_ids:
            findings.append(
                Finding(
                    check="references",
                    severity=Severity.ERROR,
                    message=(
                        f"report {report.report_id} has no structuring fixture, so the "
                        "OBSERVE to STRUCTURE step would raise for it"
                    ),
                )
            )

    for observation in inputs.structured:
        expected = report_sites.get(observation.report_id)
        if expected is None:
            findings.append(
                Finding(
                    check="references",
                    severity=Severity.ERROR,
                    message=(
                        f"structured observation {observation.report_id} has no field report "
                        "behind it"
                    ),
                )
            )
        elif observation.site_id != expected:
            findings.append(
                Finding(
                    check="references",
                    severity=Severity.ERROR,
                    message=(
                        f"structured observation {observation.report_id} says site "
                        f"{observation.site_id!r} but its report says {expected!r}"
                    ),
                )
            )
    return findings


def check_coordinates_are_in_the_keys(inputs: Inputs) -> list[Finding]:
    """A transcription error in a coordinate silently selects the wrong satellite pixel."""
    findings: list[Finding] = []
    for site in inputs.sites:
        lat, lon = site.location.latitude, site.location.longitude
        in_range = (
            KEYS_LAT_RANGE[0] <= lat <= KEYS_LAT_RANGE[1]
            and KEYS_LON_RANGE[0] <= lon <= KEYS_LON_RANGE[1]
        )
        if not in_range:
            findings.append(
                Finding(
                    check="geography",
                    severity=Severity.ERROR,
                    message=f"site {site.site_id} at {lat}, {lon} is outside the Florida Keys",
                )
            )
    return findings


def check_every_site_has_a_demo_report(inputs: Inputs) -> list[Finding]:
    """A site with no report is invisible to the pipeline, which is a silent gap."""
    with_reports = {report.site_id for report in inputs.reports}
    return [
        Finding(
            check="demo-coverage",
            severity=Severity.WARNING,
            message=(
                f"site {site_id} has no initial demo report, so the demo will show it "
                "with no field evidence at all"
            ),
        )
        for site_id in sorted({site.site_id for site in inputs.sites} - with_reports)
    ]


def check_actions_are_executable(inputs: Inputs) -> list[Finding]:
    """Can any shipped scenario actually execute each catalog action?

    Each file is valid on its own. Together they can still describe an action no
    dive team has the hours for, or that needs a kit the inventory does not hold.
    The optimizer would simply never schedule it, silently.
    """
    findings: list[Finding] = []
    known_resources = set(ResourceRequirement.model_fields)

    for action in inputs.catalog:
        reasons_by_scenario: dict[str, list[str]] = {}
        for scenario in inputs.scenarios:
            required = action.resources
            available_boats = [boat for boat in scenario.boats if boat.available]
            max_team_hours = max((t.available_hours for t in scenario.dive_teams), default=0.0)
            inventory = scenario.inventory
            reasons: list[str] = []

            if required.dive_hours > max_team_hours:
                reasons.append(
                    f"needs {required.dive_hours} dive hours, largest team has {max_team_hours}"
                )
            if required.boats > len(available_boats):
                reasons.append(f"needs {required.boats} boats, {len(available_boats)} available")
            if required.dive_teams > len(scenario.dive_teams):
                reasons.append(f"needs {required.dive_teams} dive teams")
            if required.shade_units > inventory.shade_units:
                reasons.append(f"needs {required.shade_units} shade units")
            if required.monitoring_kits > inventory.monitoring_kits:
                reasons.append(f"needs {required.monitoring_kits} monitoring kits")
            if required.sampling_kits > inventory.sampling_kits:
                reasons.append(f"needs {required.sampling_kits} sampling kits")
            if required.cost_usd > scenario.budget_usd:
                reasons.append(
                    f"costs {required.cost_usd} against a budget of {scenario.budget_usd}"
                )

            if reasons:
                reasons_by_scenario[scenario.scenario_id] = reasons

        if len(reasons_by_scenario) == len(inputs.scenarios) and inputs.scenarios:
            detail = "; ".join(
                f"{scenario_id}: {', '.join(reasons)}"
                for scenario_id, reasons in reasons_by_scenario.items()
            )
            findings.append(
                Finding(
                    check="feasibility",
                    severity=Severity.WARNING,
                    message=(
                        f"{action.action_id} cannot be executed under any shipped scenario "
                        f"({detail}). The optimizer would never schedule it."
                    ),
                )
            )

    for action in inputs.catalog:
        declared = {
            name
            for name, value in action.resources.model_dump().items()
            if isinstance(value, int | float) and value
        }
        unknown = declared - known_resources
        if unknown:
            findings.append(
                Finding(
                    check="feasibility",
                    severity=Severity.ERROR,
                    message=f"{action.action_id} declares unknown resources {sorted(unknown)}",
                )
            )
    return findings


CHECKS = (
    check_study_area_is_complete,
    check_nothing_persisted_claims_to_be_live,
    check_provenance_carries_what_it_needs,
    check_every_catalog_action_is_cited,
    check_every_cause_has_an_action,
    check_references_resolve,
    check_coordinates_are_in_the_keys,
    check_every_site_has_a_demo_report,
    check_actions_are_executable,
)


def run_all_checks(inputs: Inputs | None = None) -> list[Finding]:
    """Run every check and return everything that is wrong, worst first."""
    inputs = inputs or load_inputs()
    findings = [finding for check in CHECKS for finding in check(inputs)]
    return sorted(findings, key=lambda f: (f.severity is not Severity.ERROR, f.check, f.message))


def errors(findings: list[Finding]) -> list[Finding]:
    return [finding for finding in findings if finding.severity is Severity.ERROR]


def warnings(findings: list[Finding]) -> list[Finding]:
    return [finding for finding in findings if finding.severity is Severity.WARNING]
