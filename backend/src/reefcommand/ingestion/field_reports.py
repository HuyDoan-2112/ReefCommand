"""Field report intake and structuring.

Raw text in, StructuredObservation out.
The raw FieldReport is always retained alongside the structured form so a
reviewer can see what the extractor was working from.

For the prototype the demo reports and their structured forms are shipped as
labeled synthetic fixtures under `data/observations/`. Structuring is therefore
a deterministic lookup by report id, not a live extraction: the data lane does
not run an LLM in ingestion, and the demo reports were reconstructed from
published observations, so their structured values are known rather than
guessed. Free-text extraction of an arbitrary new report is intentionally not
implemented here.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from reefcommand.config import DATA_DIR
from reefcommand.domain.observation import FieldReport, StructuredObservation
from reefcommand.domain.provenance import FixtureSet

_OBSERVATIONS_DIR = DATA_DIR / "observations"
_REPORTS_FILE = _OBSERVATIONS_DIR / "demo_field_reports.yaml"
_UPDATES_FILE = _OBSERVATIONS_DIR / "demo_evidence_update.yaml"
_STRUCTURED_FILE = _OBSERVATIONS_DIR / "demo_structured_observations.yaml"


def _load_reports(path: Path) -> tuple[FieldReport, ...]:
    """Validate a FieldReport fixture set and return its records in file order."""
    fixtures = FixtureSet[FieldReport].model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    )
    return tuple(
        record.data.model_copy(update={"provenance_metadata": record.provenance})
        for record in fixtures.records
    )


@lru_cache(maxsize=1)
def _demo_reports() -> tuple[FieldReport, ...]:
    return _load_reports(_REPORTS_FILE)


@lru_cache(maxsize=1)
def _demo_updates() -> tuple[FieldReport, ...]:
    return _load_reports(_UPDATES_FILE)


@lru_cache(maxsize=1)
def _structured_index() -> dict[str, StructuredObservation]:
    fixtures = FixtureSet[StructuredObservation].model_validate(
        yaml.safe_load(_STRUCTURED_FILE.read_text(encoding="utf-8"))
    )
    return {
        record.data.report_id: record.data.model_copy(
            update={"provenance_metadata": record.provenance}
        )
        for record in fixtures.records
    }


def load_demo_reports(site_ids: list[str]) -> list[FieldReport]:
    """Load the labeled synthetic demo reports shipped with the prototype.

    Returns one reconstructed initial report per requested site, in the order of
    `site_ids`. Raises when a requested site has no demo report rather than
    silently returning a short list, so a typo in a site id fails loudly.
    """
    by_site = {report.site_id: report for report in _demo_reports()}
    missing = [site_id for site_id in site_ids if site_id not in by_site]
    if missing:
        raise ValueError(f"no demo field report for site(s): {', '.join(missing)}")
    return [by_site[site_id] for site_id in site_ids]


def load_demo_updates() -> list[FieldReport]:
    """Load the reconstructed follow-up reports that drive the re-planning demo.

    Currently the documented Cheeca Rocks post-bleaching disease report. These
    are submitted as new evidence after the initial plan, which is what makes the
    Coordinator reconsider and the optimizer possibly reallocate.
    """
    return list(_demo_updates())


def structure(report: FieldReport) -> StructuredObservation:
    """Return the structured signals for one field report.

    For the shipped demo reports this is a deterministic lookup of the
    structuring fixture keyed by report id, so the OBSERVE to STRUCTURE step is
    reproducible and needs no LLM in the ingestion lane. A report with no demo
    structuring fixture raises, because free-text extraction of an arbitrary
    report is not implemented here.

    Absence of a field on the returned observation means "not reported", never
    "reported as zero".
    """
    observation = _structured_index().get(report.report_id)
    if observation is None:
        raise ValueError(
            f"no structuring fixture for report {report.report_id!r}; "
            "free-text extraction is not implemented in the ingestion lane"
        )
    return observation
