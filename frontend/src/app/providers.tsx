'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';

import { ApiError } from '@/api/client';

/**
 * Do not retry a request the server has already answered definitively.
 *
 * A 404 for a site that has no plan yet, or a 422 for a rejected field report,
 * is a real answer. Retrying it three times delays showing the user the actual
 * reason. A 5xx or a dropped connection is worth one more attempt: a Coordinator
 * business-rule violation arrives as a 500, and during a live demo a transient
 * provider failure should not end the run.
 */
function shouldRetry(failureCount: number, error: Error): boolean {
  if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
    return false;
  }
  return failureCount < 1;
}

/**
 * The dashboard re-plans while the user is looking at it, so the query client
 * lives in a client component rather than at module scope. Module scope would
 * share one cache across every request on the server.
 */
export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // Plans change when evidence or capacity changes, not on a timer.
            // Refetching is driven by mutations and explicit invalidation.
            staleTime: 30_000,
            refetchOnWindowFocus: false,
            retry: shouldRetry,
          },
          mutations: {
            // A re-plan is not idempotent: retrying a submitted field report
            // would submit it twice.
            retry: false,
          },
        },
      }),
  );

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
