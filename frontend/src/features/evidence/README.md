# Evidence feature

Renders fused evidence for one site.

Rendering rules that follow from the model and are not negotiable in the UI:

- The four support scores do not sum to 1. Do not render them as a pie chart, a
  stacked bar, or percentages of a whole. Four independent bars, or a grouped
  layout, is correct.
- Label them "support", not "probability" or "likelihood".
- Show confidence alongside support. A support of 0.8 at confidence 0.3 is a
  different situation from 0.8 at 0.9, and the manager needs to see that.
- Show citations with their review status and reporting organization intact.
- When the Coordinator requested more evidence, show what it asked for and why.
  That is the product working, not the product failing.
