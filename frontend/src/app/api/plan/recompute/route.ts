import type { NextRequest } from 'next/server';

/**
 * The provider-backed seven-site run can take longer than the generic rewrite
 * proxy's socket budget. Keep this one long request same-origin while allowing
 * the backend enough time to finish and publish one complete validated plan.
 */
export const dynamic = 'force-dynamic';
export const maxDuration = 300;

const apiUrl = process.env.REEFCOMMAND_API_URL ?? 'http://127.0.0.1:8000';

export async function POST(request: NextRequest): Promise<Response> {
  const response = await fetch(`${apiUrl}/plan/recompute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: await request.text(),
    cache: 'no-store',
  });

  return new Response(response.body, {
    status: response.status,
    headers: {
      'Content-Type': response.headers.get('Content-Type') ?? 'application/json',
    },
  });
}
