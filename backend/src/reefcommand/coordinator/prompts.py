"""Coordinator prompt construction.

The prompt receives, as data:

1. The fused evidence summary from evidence/fusion.py.
2. The eligible actions from policy/engine.py, each with its unmet evidence
   requirements.

It does not receive raw tool output, and it is not asked to compute support
scores or to invent actions.
Both of those are already decided by the time the prompt is built.
"""

from __future__ import annotations

import json

from reefcommand.domain.evidence import FusedEvidence
from reefcommand.domain.intervention import EligibleAction

SYSTEM_PROMPT = """\
You are the coordinating decision layer of a reef-response planning system.

You do not diagnose. You do not invent interventions. You do not assign boats,
teams, or equipment.

You are given reconciled evidence support scores for four non-exclusive causes,
and a list of candidate actions that a deterministic policy engine has already
found eligible and source-backed for this site.

Decide one thing: is the current evidence sufficient to act on one of these
eligible actions now, or is another observation needed first.

Support scores are support scores, not probabilities. They do not sum to 1 and
the causes are not independent. Two causes can both be well supported.

Respond only with the required structured output.
"""


def build_user_prompt(evidence: FusedEvidence, actions: list[EligibleAction]) -> str:
    """Render the per-case prompt from already-computed inputs."""
    candidate_actions = [
        {
            "action_id": action.action_id,
            "priority": action.priority.value,
            "supporting_causes": [cause.value for cause in action.supporting_causes],
            "unmet_evidence_requirements": action.unmet_evidence_requirements,
            "expected_compatibility": action.expected_compatibility,
            "provenance": action.provenance,
        }
        for action in actions
    ]
    return (
        "Fused evidence:\n"
        f"{json.dumps(evidence.model_dump(mode='json'), indent=2)}\n\n"
        "Policy-eligible candidate actions:\n"
        f"{json.dumps(candidate_actions, indent=2)}\n\n"
        "If one or more candidates have no unmet requirements and the evidence supports "
        "acting, approve only those exact action_id values. Otherwise request the most "
        "useful additional evidence from the allowed enum and approve no action.\n\n"
        "Every approved_actions item must contain exactly action_id, priority, and a required "
        "rationale explaining why the current evidence supports that action. Do not copy the "
        "candidate object into approved_actions."
    )
