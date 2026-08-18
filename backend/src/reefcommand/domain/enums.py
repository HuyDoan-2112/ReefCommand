"""Enumerations shared across the pipeline.

Keeping these in one place stops each stage from inventing its own spelling of
"thermal" and makes the Coordinator's schema-constrained output enforceable.
"""

from enum import StrEnum


class Cause(StrEnum):
    """The four competing evidence categories.

    These are not mutually exclusive.
    Thermal stress and disease can both be well supported at the same site.
    """

    THERMAL = "thermal"
    DISEASE = "disease"
    RUNOFF = "runoff"
    PHYSICAL = "physical"


class Provenance(StrEnum):
    """Where a value actually came from.

    Every externally sourced value carries one of these.
    SIMULATED and SYNTHETIC are never presented to a user as real.
    """

    LIVE = "live"
    CACHE = "cache"
    SIMULATED = "simulated"
    SYNTHETIC = "synthetic"


class MonitoringProgram(StrEnum):
    """Which monitoring programme produced an ecological measurement.

    These are not interchangeable. CREMP uses fixed, permanently staked transects
    with photo point counts. NCRMP uses stratified random sampling with linear
    point intercept. A cover value from one is not a like-for-like substitute for
    a cover value from the other, which is why the programme is a required field
    on every measurement and travels to the dashboard rather than living in a note.
    """

    CREMP = "CREMP"
    NCRMP = "NCRMP"


class AlertLevel(StrEnum):
    """NOAA Coral Reef Watch bleaching alert levels.

    Definitions follow the 5km product methodology at
    coralreefwatch.noaa.gov/product/5km/.
    """

    NO_STRESS = "no_stress"
    WATCH = "watch"
    WARNING = "warning"
    ALERT_LEVEL_1 = "alert_level_1"
    ALERT_LEVEL_2 = "alert_level_2"


class ActionClass(StrEnum):
    """Candidate action classes defined by the intervention knowledge base.

    The LLM does not extend this list.
    New classes are added to the knowledge base with a cited source.
    """

    MONITORING = "monitoring"
    TARGETED_DISEASE_SURVEY = "targeted_disease_survey"
    BIOSECURITY_WORKFLOW = "biosecurity_workflow"
    WATER_QUALITY_INVESTIGATION = "water_quality_investigation"
    PHYSICAL_DAMAGE_ASSESSMENT = "physical_damage_assessment"
    TEMPORARY_SHADING = "temporary_shading"


class EvidenceRequestType(StrEnum):
    """Additional observations the Coordinator is allowed to request."""

    CLOSE_RANGE_LESION_IMAGE = "close_range_lesion_image"
    TRANSECT_PHOTO_SERIES = "transect_photo_series"
    WATER_SAMPLE = "water_sample"
    TURBIDITY_READING = "turbidity_reading"
    STRUCTURAL_DAMAGE_SURVEY = "structural_damage_survey"
    REPEAT_DIVE_COMPARISON = "repeat_dive_comparison"


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
