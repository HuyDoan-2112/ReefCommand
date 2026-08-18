/**
 * Refresh the committed OpenAPI snapshot from a running backend.
 *
 * The snapshot is committed so that `npm run gen:api`, typecheck, and CI all
 * work without a Python process. This script is the only step that needs the
 * backend up, and it is run deliberately when the contract changes rather than
 * on every build.
 *
 * Usage, from frontend/:
 *   npm run gen:api:refresh
 *
 * Start the backend first:
 *   cd backend && uv run uvicorn reefcommand.api.app:app
 */

import { writeFile } from 'node:fs/promises';
import { argv, exit } from 'node:process';

const DEFAULT_URL = 'http://127.0.0.1:8000/openapi.json';
const OUTPUT = new URL('../openapi.json', import.meta.url);

const url = argv[2] ?? DEFAULT_URL;

/**
 * Recursively sort object keys so the snapshot diff is stable across runs.
 *
 * This mirrors `json.dumps(..., sort_keys=True)` on the backend side. Arrays
 * keep their order, because order is meaningful in an OpenAPI document.
 */
function sortKeysDeep(value) {
  if (Array.isArray(value)) {
    return value.map(sortKeysDeep);
  }
  if (value === null || typeof value !== 'object') {
    return value;
  }
  return Object.fromEntries(
    Object.keys(value)
      .sort()
      .map((key) => [key, sortKeysDeep(value[key])]),
  );
}

try {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${url} returned ${response.status}`);
  }

  const spec = await response.json();
  const paths = Object.keys(spec.paths ?? {}).length;
  const schemas = Object.keys(spec.components?.schemas ?? {}).length;

  await writeFile(OUTPUT, `${JSON.stringify(sortKeysDeep(spec), null, 2)}\n`, 'utf8');

  console.log(`Wrote openapi.json from ${url}`);
  console.log(`  ${paths} paths, ${schemas} component schemas`);
  console.log('Now run: npm run gen:api');
} catch (error) {
  console.error(`Could not refresh the OpenAPI snapshot from ${url}`);
  console.error(error instanceof Error ? error.message : error);
  console.error('Is the backend running? cd backend && uv run uvicorn reefcommand.api.app:app');
  exit(1);
}
