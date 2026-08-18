/**
 * Equirectangular projection for the study area.
 *
 * The seven sites span about 1.6 degrees of longitude and 0.76 of latitude, so
 * a plate carree projection is accurate enough at this scale. Longitude is
 * scaled by cos(latitude) so the aspect ratio stays true and the Keys read as
 * the southwest arc they actually are rather than being stretched flat.
 *
 * The bounds are derived from the points passed in, not hard-coded, so adding a
 * site or changing the study area reframes the map rather than pushing a pin
 * off the edge.
 */

export interface GeoPoint {
  latitude: number;
  longitude: number;
}

export interface Projected {
  x: number;
  y: number;
}

export interface Projection {
  project: (point: GeoPoint) => Projected;
  width: number;
  height: number;
  /** Kilometres per horizontal unit, for the scale bar. */
  kmPerUnit: number;
}

const KM_PER_DEGREE_LATITUDE = 110.574;

/**
 * Build a projection that fits `points` into a box of the given width, with
 * padding expressed in the same units.
 */
export function buildProjection(
  points: readonly GeoPoint[],
  width: number,
  padding: number,
): Projection {
  if (points.length === 0) {
    return { project: () => ({ x: width / 2, y: width / 2 }), width, height: width, kmPerUnit: 1 };
  }

  const latitudes = points.map((p) => p.latitude);
  const longitudes = points.map((p) => p.longitude);

  let minLat = Math.min(...latitudes);
  let maxLat = Math.max(...latitudes);
  let minLon = Math.min(...longitudes);
  let maxLon = Math.max(...longitudes);

  // A single site, or sites on one line, would give a zero-width span and
  // divide by zero. Give any degenerate axis a small real extent.
  const MIN_SPAN = 0.02;
  if (maxLat - minLat < MIN_SPAN) {
    const mid = (maxLat + minLat) / 2;
    minLat = mid - MIN_SPAN / 2;
    maxLat = mid + MIN_SPAN / 2;
  }
  if (maxLon - minLon < MIN_SPAN) {
    const mid = (maxLon + minLon) / 2;
    minLon = mid - MIN_SPAN / 2;
    maxLon = mid + MIN_SPAN / 2;
  }

  const meanLat = (minLat + maxLat) / 2;
  const lonScale = Math.cos((meanLat * Math.PI) / 180);

  const lonSpan = (maxLon - minLon) * lonScale;
  const latSpan = maxLat - minLat;

  const inner = width - padding * 2;
  const unitsPerLonDegree = inner / lonSpan;
  const height = latSpan * unitsPerLonDegree + padding * 2;

  const project = ({ latitude, longitude }: GeoPoint): Projected => ({
    x: padding + (longitude - minLon) * lonScale * unitsPerLonDegree,
    // SVG y grows downward, so north maps to a smaller y.
    y: padding + (maxLat - latitude) * unitsPerLonDegree,
  });

  return {
    project,
    width,
    height,
    kmPerUnit: KM_PER_DEGREE_LATITUDE / unitsPerLonDegree,
  };
}
