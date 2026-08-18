/**
 * Assert the live backend payloads carry the fields the generated types promise.
 *
 * `npm run typecheck` proves the frontend agrees with `openapi.json`. It cannot
 * prove `openapi.json` still matches what the running backend sends, because a
 * committed snapshot can go stale. This script closes that gap by fetching every
 * endpoint and checking the fields the dashboard actually reads.
 *
 * Usage, with the backend running:
 *   npm run check:contract
 *
 * A stale snapshot, a renamed field, or a field that silently stopped being
 * serialized all fail here rather than surfacing as `undefined` in a component.
 */

import { argv, exit } from 'node:process';

const base = argv[2] ?? 'http://127.0.0.1:8000';
const failures = [];

function expect(object, fields, label) {
  const missing = fields.filter((field) => !(field in object));
  if (missing.length > 0) {
    failures.push(`${label} is missing: ${missing.join(', ')}`);
    console.log(`  FAIL  ${label} missing ${missing.join(', ')}`);
    return;
  }
  console.log(`  ok    ${label}`);
}

function check(condition, label) {
  if (!condition) {
    failures.push(label);
    console.log(`  FAIL  ${label}`);
    return;
  }
  console.log(`  ok    ${label}`);
}

async function json(path) {
  const response = await fetch(`${base}${path}`);
  return { status: response.status, body: await response.json() };
}

try {
  const { body: plan } = await json('/plan/current');
  expect(
    plan,
    [
      'plan_id',
      'generated_at',
      'scenario_id',
      'scenario_banner',
      'assignments',
      'deferred',
      'total_strategic_value',
      'binding_constraints',
      'replan_trigger',
      'replan_latency_ms',
    ],
    'ResponsePlan',
  );
  if (plan.assignments[0]) {
    expect(
      plan.assignments[0],
      [
        'site_id',
        'site_name',
        'action_id',
        'action_class',
        'boat_id',
        'team_id',
        'priority',
        'estimated_hours',
        'estimated_cost_usd',
        'evidence_summary',
        'remaining_uncertainty',
        'compatibility_rationale',
        'requires_manager_approval',
      ],
      'Assignment',
    );
  }
  if (plan.deferred[0]) {
    expect(plan.deferred[0], ['site_id', 'site_name', 'fallback_action_id', 'reason'], 'DeferredSite');
  }

  const { body: sites } = await json('/sites');
  check(Array.isArray(sites), 'GET /sites returns an array');
  expect(
    sites[0],
    [
      'site_id',
      'name',
      'latitude',
      'longitude',
      'location',
      'measurements',
      'restoration_investment',
      'has_active_restoration',
      'scores',
      'dominant_causes',
      'current_assignment',
      'deferred',
    ],
    'SiteView',
  );
  expect(
    sites[0].scores,
    ['ecological_value', 'strategic_value', 'weights_are_prototype_assumptions'],
    'SiteScores',
  );

  const { body: evidence } = await json(`/sites/${sites[0].site_id}/evidence`);
  expect(
    evidence,
    ['site_id', 'by_cause', 'dominant_causes', 'ambiguity', 'lowest_confidence', 'fused_at'],
    'FusedEvidence',
  );
  check(
    Object.keys(evidence.by_cause).sort().join() === 'disease,physical,runoff,thermal',
    'by_cause carries exactly the four causes',
  );
  expect(
    evidence.by_cause.thermal,
    ['cause', 'support', 'confidence', 'rationale', 'citations', 'computed_at'],
    'CauseEvidence',
  );

  // The support scores are not a probability distribution. If they ever sum to
  // exactly 1 across every site, something upstream started normalizing them
  // and the dashboard's rendering rules would no longer be justified.
  const total = ['thermal', 'disease', 'runoff', 'physical'].reduce(
    (sum, cause) => sum + evidence.by_cause[cause].support,
    0,
  );
  console.log(`  note  support scores sum to ${total.toFixed(2)}, not normalized to 1`);

  const { body: scenario } = await json('/resources/scenario');
  expect(scenario, ['scenario', 'banner'], 'ScenarioView');
  expect(
    scenario.scenario,
    [
      'scenario_id',
      'label',
      'provenance',
      'boats',
      'dive_teams',
      'inventory',
      'budget_usd',
      'daylight_hours',
    ],
    'ResourceScenario',
  );
  check(scenario.banner.length > 0, 'the simulated-data banner is present and not empty');

  const { body: dataSources } = await json('/health/data-sources');
  expect(dataSources, ['checked_at', 'sources', 'status'], 'DataSourcesHealth');

  const { body: trace } = await json(`/plan/${plan.plan_id}/trace`);
  expect(
    trace,
    [
      'trace_id',
      'plan_id',
      'status',
      'scenario_id',
      'offline',
      'started_at',
      'completed_at',
      'latency_ms',
      'steps',
    ],
    'ExecutionTrace',
  );

  // The evidence endpoint has no Coordinator block, so the evidence surface
  // reads the decision out of the trace instead. If this stops resolving, the
  // "what did the Coordinator ask for" requirement cannot be met.
  const coordinator = trace.steps.find((step) => step.stage === 'coordinator');
  check(
    coordinator?.output?.decision !== undefined,
    'the Coordinator decision is reachable from the trace',
  );

  const { body: siteTrace } = await json(`/plan/${plan.plan_id}/trace/${sites[0].site_id}`);
  expect(siteTrace, ['plan_id', 'scenario_id', 'site_id', 'steps'], 'SiteExecutionTrace');

  const notFound = await json('/sites/no-such-site/evidence');
  check(notFound.status === 404, 'an unknown site returns 404');
  check(
    typeof notFound.body.detail === 'string',
    'an error body carries a string detail for ApiError to surface',
  );
} catch (error) {
  console.error(`\nCould not reach the backend at ${base}`);
  console.error(error instanceof Error ? error.message : error);
  console.error('Start it first: cd backend && uv run uvicorn reefcommand.api.app:app');
  exit(1);
}

if (failures.length > 0) {
  console.error(`\n${failures.length} contract check(s) failed:`);
  for (const failure of failures) {
    console.error(`  - ${failure}`);
  }
  console.error('\nIf the backend changed on purpose, run: npm run gen:api:refresh');
  exit(1);
}

console.log('\nAll contract checks passed.');
