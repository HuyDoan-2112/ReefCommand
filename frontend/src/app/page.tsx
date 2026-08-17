/**
 * The main dashboard surface.
 *
 * Composition only. Feature logic lives under src/features.
 */
export default function PlanPage() {
  return (
    <main className="page">
      <h1>ReefCommand</h1>
      <p className="page__subtitle">
        Reef managers do not have a lack-of-data problem. They have a
        decision-under-resource-constraints problem.
      </p>
      {/* TODO: SimulatedDataBanner, CurrentPlan, EvidencePanel, ResourcePanel, EvaluationPanel */}
    </main>
  );
}
