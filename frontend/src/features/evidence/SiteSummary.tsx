'use client';

import Link from 'next/link';

import { Panel, ProvenanceBadge } from '@/components';
import { useSites } from '@/hooks/useSites';

import { EvidencePanel } from './EvidencePanel';

import styles from './SiteSummary.module.css';

/**
 * Identity and scores for one site.
 *
 * A partial surface on purpose: the evidence breakdown and the Coordinator's
 * decision arrive in step 5. It exists now so the map pins link somewhere real
 * rather than a 404.
 *
 * Both scores are shown, never blended. `strategic_value` is what the optimizer
 * is wired to; `ecological_value` is the investment-agnostic number for when
 * someone asks what the reef needs regardless of what has been spent there.
 * The prototype-assumption disclaimer travels with them.
 */
export function SiteSummary({ siteId }: { siteId: string }) {
  const { data: sites, isPending, error } = useSites();

  if (isPending) return <p className={styles.muted}>Loading site...</p>;
  if (error) return <p className={styles.muted}>Could not load sites: {error.message}</p>;

  const site = sites.find((candidate) => candidate.site_id === siteId);
  if (!site) {
    return (
      <p className={styles.muted}>
        No site called {siteId}. <Link href="/">Back to the Command Map</Link>.
      </p>
    );
  }

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <div>
          <h2 className={styles.name}>{site.name}</h2>
          <div className={styles.coords}>
            {site.latitude.toFixed(4)}&deg; N, {Math.abs(site.longitude).toFixed(4)}&deg; W
            {site.location.zone_name_in_source ? ` (${site.location.zone_name_in_source})` : ''}
          </div>
        </div>
        <div className={styles.headerTags}>
          <ProvenanceBadge
            provenance={site.location.provenance.kind}
            title={site.location.provenance.source}
          />
          {site.has_active_restoration ? (
            <span className={styles.tag}>Active restoration</span>
          ) : null}
        </div>
      </header>

      <div className={styles.scoreRow}>
        <Panel title="Strategic value" hint="drives allocation">
          <div className={styles.score}>{site.scores.strategic_value.toFixed(2)}</div>
          <p className={styles.scoreNote}>
            Ecological value weighted with prior restoration investment. This is the number the
            optimizer maximises.
          </p>
        </Panel>
        <Panel title="Ecological value" hint="investment agnostic">
          <div className={styles.score}>{site.scores.ecological_value.toFixed(2)}</div>
          <p className={styles.scoreNote}>
            Coral cover and species richness only. What the reef needs, independent of what has
            already been spent there.
          </p>
        </Panel>
      </div>

      {site.scores.weights_are_prototype_assumptions ? (
        <p className={styles.disclaimer}>
          The weights behind both scores are stated prototype assumptions, not scientific claims.
        </p>
      ) : null}

      <EvidencePanel siteId={site.site_id} />
    </div>
  );
}
