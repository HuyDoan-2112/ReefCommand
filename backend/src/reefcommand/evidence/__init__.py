"""Four competing cause investigators plus deterministic fusion.

The four causes are not mutually exclusive.
Each investigator produces an independent support score with its own confidence.
Scores are not normalized against each other and the causes are not assumed
statistically independent.

thermal.py is deterministic on purpose. Do not use an LLM to compare numeric
thresholds.
"""
