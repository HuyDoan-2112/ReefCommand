'use client';

/**
 * Execution trace queries.
 *
 * The trace is the only place the Coordinator's decision is exposed, including
 * any request for additional evidence. `GET /sites/{id}/evidence` carries the
 * fused support scores but no Coordinator block, so the evidence surface needs
 * both.
 *
 * Traces are immutable once a plan is finished, so they never go stale.
 */

import { useQuery } from '@tanstack/react-query';

import { fetchExecutionTrace, fetchSiteTrace } from '@/api/endpoints';
import { queryKeys } from '@/hooks/queryKeys';

export function useExecutionTrace(planId: string | null) {
  return useQuery({
    queryKey: queryKeys.trace(planId ?? ''),
    queryFn: () => fetchExecutionTrace(planId as string),
    enabled: planId !== null,
    staleTime: Infinity,
    retry: false,
  });
}

export function useSiteTrace(planId: string | null, siteId: string | null) {
  return useQuery({
    queryKey: queryKeys.siteTrace(planId ?? '', siteId ?? ''),
    queryFn: () => fetchSiteTrace(planId as string, siteId as string),
    enabled: planId !== null && siteId !== null,
    staleTime: Infinity,
    retry: false,
  });
}
