'use client';

import Link from 'next/link';
import { useState } from 'react';

import { useCurrentPlan } from '@/hooks/usePlan';
import { cx } from '@/lib/cx';
import { useSiteEvidenceBatch, useSites } from '@/hooks/useSites';
import type { FusedEvidence, SiteView } from '@/types';

import styles from './SiteMap.module.css';
import { buildProjection } from './projection';

/**
 * The seven study-area sites plotted at their real coordinates.
 *
 * The reference draws four hand-positioned blobs shaped like Maui Nui. Those
 * are not carried over. Pin positions here come from the `latitude` and
 * `longitude` the API returns for each site, projected in `projection.ts`, so
 * the map cannot drift out of agreement with the data.
 *
 * The island chain behind the pins is explicitly schematic and labelled as
 * such. It is drawn from a handful of waypoints along the Keys to give the
 * reader somewhere to stand, not to assert a coastline. The pins are the
 * accurate part, and the caption says so.
 *
 * Pins are coloured by what the plan does with each site, not by a severity
 * rating. This is an operations map: the question it answers is which reefs are
 * being visited today and which are not. Severity would need a single number to
 * stand for a site, which the four-cause model deliberately refuses.
 */

const MAP_WIDTH = 900;
const MAP_PADDING = 64;

/** Waypoints tracing the Keys island chain, northwest of the reef line. */
const KEYS_OUTLINE: ReadonlyArray<{ latitude: number; longitude: number }> = [
  { latitude: 25.32, longitude: -80.28 },
  { latitude: 25.18, longitude: -80.4 },
  { latitude: 25.02, longitude: -80.53 },
  { latitude: 24.92, longitude: -80.68 },
  { latitude: 24.82, longitude: -80.83 },
  { latitude: 24.72, longitude: -81.02 },
  { latitude: 24.7, longitude: -81.22 },
  { latitude: 24.68, longitude: -81.4 },
  { latitude: 24.64, longitude: -81.6 },
  { latitude: 24.57, longitude: -81.8 },
  { latitude: 24.55, longitude: -81.95 },
];

type PlanStatus = 'clear' | 'watch' | 'serious' | 'critical';

const STATUS_LABEL: Record<PlanStatus, string> = {
  clear: 'Clear - no eligible action',
  watch: 'Watch - deferred this cycle',
  serious: 'Serious - response assigned',
  critical: 'Critical - high-priority assignment',
};

const STATUS_CLASS: Record<PlanStatus, string | undefined> = {
  clear: styles.pinUntasked,
  watch: styles.pinDeferred,
  serious: styles.pinSerious,
  critical: styles.pinTasked,
};

function statusOf(site: SiteView): PlanStatus {
  if (site.current_assignment?.priority === 'high') return 'critical';
  if (site.current_assignment) return 'serious';
  if (site.deferred) return 'watch';
  return 'clear';
}

function smoothPath(points: ReadonlyArray<{ x: number; y: number }>): string {
  if (points.length < 2) return '';
  const [first, ...rest] = points;
  let d = `M ${first!.x} ${first!.y}`;
  for (let i = 0; i < rest.length; i += 1) {
    const previous = i === 0 ? first! : rest[i - 1]!;
    const current = rest[i]!;
    const midX = (previous.x + current.x) / 2;
    const midY = (previous.y + current.y) / 2;
    d += ` Q ${previous.x} ${previous.y} ${midX} ${midY}`;
  }
  const last = rest[rest.length - 1]!;
  d += ` L ${last.x} ${last.y}`;
  return d;
}

function reportCitations(evidence: FusedEvidence | undefined) {
  if (!evidence) return [];

  return Object.values(evidence.by_cause).flatMap((cause) =>
    (cause?.citations ?? []).filter((citation) =>
      citation.source.toLowerCase().startsWith('structured form of demo report'),
    ),
  );
}

function uniqueReportCount(evidence: FusedEvidence | undefined): number {
  return new Set(reportCitations(evidence).map((citation) => citation.reference ?? citation.source))
    .size;
}

function provenanceLabel(values: ReadonlySet<string>, isPending: boolean): string {
  if (isPending) return 'loading';
  if (values.size === 0) return 'unavailable';
  if (values.size > 1) return 'mixed sources';
  const [value] = values;
  return value ?? 'unavailable';
}

export function SiteMap() {
  const { data: sites, isPending, error } = useSites();
  const { data: plan } = useCurrentPlan();
  const [showThermal, setShowThermal] = useState(false);
  const [showReports, setShowReports] = useState(true);
  const siteIds = sites?.map((site) => site.site_id) ?? [];
  const evidenceQueries = useSiteEvidenceBatch(siteIds);

  if (isPending) {
    return <div className={styles.placeholder}>Loading the study area...</div>;
  }

  if (error) {
    return <div className={styles.placeholder}>Could not load sites: {error.message}</div>;
  }

  if (sites.length === 0) {
    return (
      <div className={styles.placeholder}>
        No sites yet. The study area appears once a plan has been computed.
      </div>
    );
  }

  const projection = buildProjection(
    [...sites, ...KEYS_OUTLINE.map((p) => ({ latitude: p.latitude, longitude: p.longitude }))],
    MAP_WIDTH,
    MAP_PADDING,
  );

  const outline = KEYS_OUTLINE.map((point) => projection.project(point));
  const landPath = smoothPath(outline);

  // A round-number scale bar, sized from the projection rather than guessed.
  const targetKm = 25;
  const scaleUnits = targetKm / projection.kmPerUnit;

  const counts = sites.reduce<Record<PlanStatus, number>>(
    (acc, site) => {
      acc[statusOf(site)] += 1;
      return acc;
    },
    { clear: 0, watch: 0, serious: 0, critical: 0 },
  );

  const evidenceBySite = new Map(
    siteIds.map((siteId, index) => [siteId, evidenceQueries[index]?.data] as const),
  );
  const evidencePending = evidenceQueries.some((query) => query.isPending);
  const thermalProvenance = new Set(
    evidenceQueries.flatMap((query) =>
      (query.data?.by_cause.thermal?.citations ?? []).map((citation) => citation.provenance),
    ),
  );
  const reportProvenance = new Set(
    evidenceQueries.flatMap((query) =>
      reportCitations(query.data).map((citation) => citation.provenance),
    ),
  );

  return (
    <div className={styles.wrap}>
      <svg
        className={styles.svg}
        viewBox={`0 0 ${projection.width} ${projection.height}`}
        role="img"
        aria-label={`Map of ${sites.length} Florida Keys reef sites. ${counts.critical + counts.serious} tasked, ${counts.watch} deferred.`}
      >
        <defs>
          <linearGradient id="ocean" x1="0" y1="0" x2="0.4" y2="1">
            <stop offset="0%" stopColor="#1391b4" />
            <stop offset="45%" stopColor="#0a4a5f" />
            <stop offset="100%" stopColor="#073b4c" />
          </linearGradient>
          <linearGradient id="land" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#3a9c74" />
            <stop offset="100%" stopColor="#1f6e50" />
          </linearGradient>
          <filter id="landGlow" x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="7" />
          </filter>
          <radialGradient id="thermalHeat">
            <stop offset="0%" stopColor="#ff6b55" stopOpacity="0.9" />
            <stop offset="42%" stopColor="#ff9e55" stopOpacity="0.52" />
            <stop offset="100%" stopColor="#ffd166" stopOpacity="0" />
          </radialGradient>
        </defs>

        <rect x="0" y="0" width={projection.width} height={projection.height} fill="url(#ocean)" />

        {/* Shallow-water halo, then the island chain itself. */}
        <path
          d={landPath}
          stroke="rgba(247,235,200,0.35)"
          strokeWidth="34"
          strokeLinecap="round"
          fill="none"
          filter="url(#landGlow)"
        />
        <path d={landPath} stroke="url(#land)" strokeWidth="17" strokeLinecap="round" fill="none" />

        {showThermal
          ? sites.map((site) => {
              const thermal = evidenceBySite.get(site.site_id)?.by_cause.thermal;
              if (!thermal) return null;
              const { x, y } = projection.project(site);
              const radius = 22 + thermal.support * 34;
              return (
                <g key={`thermal-${site.site_id}`} className={styles.thermalLayer}>
                  <title>
                    {site.name}. Thermal support {thermal.support.toFixed(2)}, confidence{' '}
                    {thermal.confidence.toFixed(2)}. This is evidence support, not probability.
                  </title>
                  <circle
                    cx={x}
                    cy={y}
                    r={radius}
                    fill="url(#thermalHeat)"
                    opacity={0.28 + thermal.support * 0.62}
                  />
                  <circle
                    cx={x}
                    cy={y}
                    r={10 + thermal.support * 9}
                    className={styles.thermalCore}
                  />
                </g>
              );
            })
          : null}

        {sites.map((site) => {
          const { x, y } = projection.project(site);
          const status = statusOf(site);
          return (
            <Link key={site.site_id} href={`/sites/${site.site_id}`} className={styles.pinLink}>
              <g className={styles.pinGroup}>
                <title>
                  {site.name}. {STATUS_LABEL[status]}. Strategic value{' '}
                  {site.scores.strategic_value.toFixed(2)}.
                </title>
                {status === 'critical' || status === 'serious' ? (
                  <circle
                    cx={x}
                    cy={y}
                    r="9"
                    className={cx(styles.pulse, status === 'serious' && styles.pulseSerious)}
                  />
                ) : null}
                <circle cx={x} cy={y} r="7" className={STATUS_CLASS[status]} />
                <text x={x} y={y - 14} className={styles.pinLabel} textAnchor="middle">
                  {site.name}
                </text>
              </g>
            </Link>
          );
        })}

        {showReports
          ? sites.map((site) => {
              const reportCount = uniqueReportCount(evidenceBySite.get(site.site_id));
              if (reportCount === 0) return null;
              const { x, y } = projection.project(site);
              return (
                <Link
                  key={`reports-${site.site_id}`}
                  href={`/sites/${site.site_id}`}
                  className={styles.reportLink}
                  aria-label={`${reportCount} synthetic diver report fixture${reportCount === 1 ? '' : 's'} for ${site.name}`}
                >
                  <g className={styles.reportMarker} transform={`translate(${x + 14} ${y + 9})`}>
                    <title>
                      {site.name}: {reportCount} synthetic diver report fixture
                      {reportCount === 1 ? '' : 's'} cited by current evidence.
                    </title>
                    <circle r="10" className={styles.reportMarkerBase} />
                    <text x="0" y="3.5" textAnchor="middle" className={styles.reportIcon}>
                      🤿
                    </text>
                    <circle cx="9" cy="8" r="7" className={styles.reportCountBase} />
                    <text x="9" y="11" textAnchor="middle" className={styles.reportCount}>
                      {reportCount}
                    </text>
                  </g>
                </Link>
              );
            })
          : null}

        {/* Scale bar */}
        <g transform={`translate(${MAP_PADDING}, ${projection.height - 26})`}>
          <line x1="0" y1="0" x2={scaleUnits} y2="0" className={styles.scaleLine} />
          <line x1="0" y1="-4" x2="0" y2="4" className={styles.scaleLine} />
          <line x1={scaleUnits} y1="-4" x2={scaleUnits} y2="4" className={styles.scaleLine} />
          <text x={scaleUnits / 2} y="-8" className={styles.scaleText} textAnchor="middle">
            {targetKm} km
          </text>
        </g>
      </svg>

      <div className={styles.mapTitleCard}>
        <strong>Florida Keys Reef Network</strong>
        <span>Current-plan evidence layers</span>
      </div>

      <div className={styles.layerControls} aria-label="Map evidence layers">
        <button
          type="button"
          role="switch"
          aria-checked={showThermal}
          className={styles.layerButton}
          onClick={() => setShowThermal((visible) => !visible)}
        >
          <span className={styles.layerName}>🌡️ Satellite thermal stress</span>
          <span className={styles.layerSource}>
            {provenanceLabel(thermalProvenance, evidencePending)}
          </span>
          <span className={cx(styles.toggle, showThermal && styles.toggleOn)} aria-hidden="true">
            <span />
          </span>
        </button>
        <button
          type="button"
          role="switch"
          aria-checked={showReports}
          className={styles.layerButton}
          onClick={() => setShowReports((visible) => !visible)}
        >
          <span className={styles.layerName}>🤿 Diver reports</span>
          <span className={styles.layerSource}>
            {provenanceLabel(reportProvenance, evidencePending)}
          </span>
          <span className={cx(styles.toggle, showReports && styles.toggleOn)} aria-hidden="true">
            <span />
          </span>
        </button>
        <p className={styles.layerNote}>Thermal color shows support, not probability.</p>
      </div>

      <div className={styles.legend}>
        <div className={styles.legendTitle}>Plan response status</div>
        {(['clear', 'watch', 'serious', 'critical'] as const).map((status) => (
          <div key={status} className={styles.legendRow}>
            <span className={cx(styles.legendSwatch, STATUS_CLASS[status])} />
            {STATUS_LABEL[status]}
            <span className={styles.legendCount}>{counts[status]}</span>
          </div>
        ))}
        {plan ? (
          <div className={styles.legendNote}>
            Operational status, not overall reef health. Scenario {plan.scenario_id}. Pins use
            reported site coordinates.
          </div>
        ) : null}
      </div>

      <p className={styles.caption}>
        Site positions are the coordinates the API reports for each reef. The island chain behind
        them is a schematic outline of the Keys drawn for orientation, not a surveyed coastline.
      </p>
    </div>
  );
}
