'use client';

/**
 * Capacity scenario and data-source provenance queries.
 *
 * The scenario carries the simulated-data banner, which the UI must never drop.
 */

import { useQuery } from '@tanstack/react-query';

import { fetchDataSources, fetchScenario } from '@/api/endpoints';
import { queryKeys } from '@/hooks/queryKeys';

export function useScenario() {
  return useQuery({
    queryKey: queryKeys.scenario(),
    queryFn: fetchScenario,
  });
}

/**
 * Per-source live-versus-cache standing.
 *
 * Reports `status: "no_plan"` with an empty source list before the first plan,
 * and never triggers a planning run.
 */
export function useDataSources() {
  return useQuery({
    queryKey: queryKeys.dataSources(),
    queryFn: fetchDataSources,
  });
}
