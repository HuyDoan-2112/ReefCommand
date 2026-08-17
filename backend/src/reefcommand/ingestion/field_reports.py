"""Field report intake and structuring.

Raw text in, StructuredObservation out.
The raw FieldReport is always retained alongside the structured form so a
reviewer can see what the extractor was working from.
"""

from __future__ import annotations

from reefcommand.domain.observation import FieldReport, StructuredObservation


def load_demo_reports(site_ids: list[str]) -> list[FieldReport]:
    """Load the labeled synthetic demo reports shipped with the prototype."""
    raise NotImplementedError


def structure(report: FieldReport) -> StructuredObservation:
    """Extract structured signals from one free-text field report.

    Absence of a field means "not reported", never "reported as zero".
    Anything the extractor was unsure about goes into `extraction_notes` rather
    than being silently dropped.
    """
    raise NotImplementedError
