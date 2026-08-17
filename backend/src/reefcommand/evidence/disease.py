"""Disease investigator. LLM plus a grounded tool.

LLM reasoning earns its place here because field evidence arrives as description:
lesions, tissue loss, affected species, spatial progression, disease-like
morphology.

Grounded tool: ingestion.agrra_sctld, the AGRRA Caribbean Coral Health Watch /
SCTLD Tracking Map. This is a real, specific tool call, not a generic placeholder.

Proximity rule, enforced here and not delegated to the prompt: geographic
proximity to a reviewed record is supporting evidence, not confirmation.
Proximity feeds the disease support score alongside the lesion description.
It is never a binary override, and it never on its own establishes that a new
field report is SCTLD.

Record metadata from the tracker (submission date, review status, reporting
organization) is preserved into CauseEvidence.citations.
"""

from __future__ import annotations

from reefcommand.domain.enums import Cause
from reefcommand.domain.evidence import CauseEvidence
from reefcommand.domain.observation import StructuredObservation
from reefcommand.domain.site import ReefSite

cause: Cause = Cause.DISEASE

DEFAULT_SEARCH_RADIUS_KM = 25.0


def assess(site: ReefSite, observations: list[StructuredObservation]) -> CauseEvidence:
    """Combine lesion description with nearby reviewed records into a support score."""
    raise NotImplementedError
