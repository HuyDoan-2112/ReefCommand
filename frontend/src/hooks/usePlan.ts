'use client';

/**
 * Plan queries and the two mutations that cause a re-plan.
 *
 * Both re-plan triggers, a new field report and a capacity change, invalidate
 * the same cache set through `invalidateAfterReplan`. A new plan changes the
 * plan itself, every site's standing in it, the fused evidence, the active
 * scenario, and the provenance standing, so anything less than that leaves the
 * dashboard showing a mix of two different plans.
 */

import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query';

import {
  changeScenario,
  fetchCurrentPlan,
  recomputePlan,
  structureObservation,
  submitObservation,
  submitStructuredObservation,
} from '@/api/endpoints';
import { queryKeys } from '@/hooks/queryKeys';
import type { ResponsePlan } from '@/types';

/**
 * Drop everything derived from the previous plan.
 *
 * `queryKeys.all` is the prefix for every key in the app, so this is one call
 * rather than a list that a future surface could be forgotten from. The trace
 * keys are scoped by plan id, so old traces simply become unreferenced.
 */
function invalidateAfterReplan(client: QueryClient): Promise<void> {
  return client.invalidateQueries({ queryKey: queryKeys.all });
}

export function useCurrentPlan() {
  return useQuery({
    queryKey: queryKeys.currentPlan(),
    queryFn: fetchCurrentPlan,
  });
}

/**
 * Submit a field report.
 *
 * The response already carries the new plan, so it is written straight into the
 * cache before invalidation. That way the plan surface updates from the
 * mutation response rather than waiting on a refetch, which is what makes the
 * measured `replan_latency_ms` the honest number to display.
 */
export function useSubmitObservation() {
  const client = useQueryClient();

  return useMutation({
    mutationFn: submitObservation,
    onSuccess: async (result) => {
      client.setQueryData<ResponsePlan>(queryKeys.currentPlan(), result.plan);
      await invalidateAfterReplan(client);
    },
  });
}

/** Run only the reviewed, schema-constrained report extraction stage. */
export function useStructureObservation() {
  return useMutation({ mutationFn: structureObservation });
}

/** Submit the reviewed extraction and trigger re-planning without re-extracting it. */
export function useSubmitStructuredObservation() {
  const client = useQueryClient();

  return useMutation({
    mutationFn: submitStructuredObservation,
    onSuccess: async (result) => {
      client.setQueryData<ResponsePlan>(queryKeys.currentPlan(), result.plan);
      await invalidateAfterReplan(client);
    },
  });
}

/** Change the capacity scenario. Re-runs the optimizer only, not the investigators. */
export function useChangeScenario() {
  const client = useQueryClient();

  return useMutation({
    mutationFn: changeScenario,
    onSuccess: async (result) => {
      client.setQueryData<ResponsePlan>(queryKeys.currentPlan(), result.plan);
      await invalidateAfterReplan(client);
    },
  });
}

/** Force a full recompute. For the demo and for debugging, not the normal loop. */
export function useRecomputePlan() {
  const client = useQueryClient();

  return useMutation({
    mutationFn: recomputePlan,
    onSuccess: async (plan, request) => {
      // A live site diagnosis is intentionally scoped to one site. Keep the
      // global plan cache intact so the Command Map continues to show every
      // reef while the site page reads the returned single-site trace.
      if (request?.execution_mode === 'live_llm' && request.site_ids?.length === 1) return;
      client.setQueryData<ResponsePlan>(queryKeys.currentPlan(), plan);
      await invalidateAfterReplan(client);
    },
  });
}
