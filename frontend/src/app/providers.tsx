'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';

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
          },
        },
      }),
  );

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
