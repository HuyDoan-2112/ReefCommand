import type { NextRequest } from 'next/server';

/** Give one provider-backed extraction enough time to finish and validate. */
export const dynamic = 'force-dynamic';
export const maxDuration = 60;

const apiUrl = process.env.REEFCOMMAND_API_URL ?? 'http://127.0.0.1:8000';

export async function POST(request: NextRequest): Promise<Response> {
  const response = await fetch(`${apiUrl}/observations/structure`, {
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
