import type { NextConfig } from 'next';

/**
 * The dashboard talks to the Python backend through a same-origin `/api` path,
 * so no CORS configuration is needed in development or in production.
 *
 * In development this rewrites to the local uvicorn process. On Vercel it
 * rewrites to whatever REEFCOMMAND_API_URL points at, since the Python backend
 * is deployed separately. See docs/tech-decisions.md ADR-011.
 */
const apiUrl = process.env.REEFCOMMAND_API_URL ?? 'http://127.0.0.1:8000';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [{ source: '/api/:path*', destination: `${apiUrl}/:path*` }];
  },
};

export default nextConfig;
