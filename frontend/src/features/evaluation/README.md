# Evaluation feature

Renders the evaluation results from docs/evaluation.md.

Rules:

- Report each evidence module's check separately. Never one combined accuracy
  number. Rolling them together recreates the fused-versus-single-cause mismatch
  the evaluation design exists to avoid.
- For the thermal IoU, use the wording "consistent with NOAA's own designation",
  not "proven correct". Bleaching Alert Area is a reasonable comparison point but
  not an independently-verified ground truth.
- For the optimizer comparison, state that it compares two policies inside the
  same defined problem and makes no claim about the real ocean.
