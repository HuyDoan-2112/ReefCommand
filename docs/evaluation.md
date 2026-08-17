# Evaluation

Do not claim ReefCommand "saves coral".
That is not measurable here.
Report what is measurable, and be upfront about what each number can and cannot prove.

## A. Thermal-evidence check against NOAA's own signal

Compare the thermal-evidence module output only, before fusion, against NOAA's Bleaching Alert Area polygon for the same sites and dates.

```text
IoU = (predicted high-heat-stress cells INTERSECT NOAA Bleaching Alert Area cells)
      -----------------------------------------------------------------------
      (predicted high-heat-stress cells UNION NOAA Bleaching Alert Area cells)
```

Never compare the fused compound score against Bleaching Alert Area.
NOAA's product represents heat-stress-related bleaching risk specifically.
It says nothing about disease, runoff, or physical damage.
Comparing a four-cause fused score against a single-cause reference product is a scientific mismatch and produces a misleading number.

Expect this IoU to score very high, because both sides compute the same DHW-threshold logic.
It is primarily a pipeline-correctness check: did we implement the thresholds right, did we pull the right grid cells.
It is not a novel scientific claim.

### The caveat, stated and not hidden

NOAA Coral Reef Watch's own methodology documentation acknowledges that the field observations historically used to set the 4 degree-C-week and 8 degree-C-week bleaching thresholds are informal reports, "not calibrated/validated with corresponding satellite data" (`coralreefwatch.noaa.gov/product/50km/methodology.php`).
NOAA also states it does not conduct its own in-water surveys, and relies on partner and citizen-science field reports to ground-truth its satellite products (`coralreefwatch.noaa.gov/satellite/education/monitoring.php`).

Two honest implications:

1. Bleaching Alert Area is a reasonable comparison point but not an independently-verified ground truth. Say "consistent with NOAA's own designation", not "proven correct".
2. This is a point in ReefCommand's favor. NOAA's product depends on structured field reports to stay accurate. A system that captures and fuses those reports systematically, instead of an ad hoc email, is doing a version of what the agency already says it needs.

## Per-module checks

Evaluate the other three modules separately, against evidence relevant to each.
Do not force them through the NOAA comparison.
Report each check separately on the dashboard.
Never roll them into one combined accuracy number.

| Module | Compared against |
| --- | --- |
| Disease | AGRRA SCTLD Tracking Map records for the same sites and window. Proximity to a reviewed outbreak, not NOAA thermal data. |
| Runoff | The rainfall and turbidity signal actually used as input. Internal consistency check, not an external labeled benchmark unless one is sourced. |
| Physical | Storm-track and vessel-activity records for the same window, where available. |

## B. Optimizer quality against a naive baseline

This follows systematic conservation planning, an established discipline built around comparing optimized site-selection solutions against simpler baselines.
Foundational framework: Margules and Pressey, Nature, 2000.
Tools such as Marxan are standard in this field, and published studies routinely report the gap between an optimized allocation and a baseline.
A peer-reviewed comparison of exact solvers against Marxan's default algorithm found 12 to 30 percent lower cost for the same conservation outcome (PMC7261139).
Reporting a percentage difference between a baseline policy and an optimized one is standard practice in this literature.

Hold resources fixed at the simulated scenario and compare, on the same replayed evidence stream:

- Baseline: respond to whichever site reported an issue first, or has the single highest raw DHW.
- ReefCommand: evidence-reconciled priority times `strategic_value`, solved by the constrained optimizer.

Report total `strategic_value` protected under each policy.
This percentage is a claim we are allowed to make, because it compares two policies inside the same defined problem and makes no claim about the real ocean.

## C. Re-planning responsiveness

Time, or step count, from a new piece of evidence being submitted to the dashboard showing an updated plan.
Show this live in the demo.
The re-planning loop is the strongest thing to demonstrate, so it should also be the thing we can put a number on.
