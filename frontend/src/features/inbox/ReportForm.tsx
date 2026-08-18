'use client';

import Link from 'next/link';

import { Button, Panel, ProvenanceBadge, StatTile } from '@/components';
import { useSubmitObservation } from '@/hooks/usePlan';

import styles from './ReportForm.module.css';
import { DEMO_REPORTS, type DemoReport } from './demoReports';

/**
 * The backend currently structures only named fixture reports.
 * This surface makes that boundary visible while preserving the reference
 * inbox layout and its raw-report to structured-observation flow.
 */
export function ReportForm() {
  const submit = useSubmitObservation();
  const selected = DEMO_REPORTS[0]!;

  function send(report: DemoReport) {
    submit.mutate({
      report_id: report.report_id,
      site_id: report.site_id,
      observed_at: report.observed_at,
      observer: report.observer,
      text: report.text,
      image_refs: [],
      provenance: 'synthetic',
    });
  }

  return (
    <div className={styles.root}>
      <div className={styles.statRow}>
        <StatTile
          label="📥 Demo reports ready"
          value={DEMO_REPORTS.length}
          note="backend-supported fixture"
          decoration="📥"
        />
        <StatTile
          label="🧩 Structuring mode"
          value="Fixture"
          note="not free-text LLM extraction"
          decoration="🧩"
        />
        <StatTile
          label="🚩 Review status"
          value="Required"
          note="manager approval remains mandatory"
          decoration="🚩"
        />
      </div>

      <div className={styles.inboxLayout}>
        <Panel
          title="Incoming reports"
          actions={
            <ProvenanceBadge
              provenance="synthetic"
              title="These are demo observations, not real dive reports"
            />
          }
        >
          <div className={styles.reportList}>
            {DEMO_REPORTS.map((report) => (
              <article key={report.report_id} className={styles.reportActive}>
                <header className={styles.reportHead}>
                  <span className={styles.reportSite}>{report.site_name}</span>
                  <span className={styles.unreadDot} aria-label="Ready to submit" />
                </header>
                <div className={styles.reportMeta}>
                  {report.observer} · {new Date(report.observed_at).toLocaleDateString()}
                </div>
                <p className={styles.reportPreview}>{report.text}</p>
                <span className={styles.reportStatus}>Selected demo report</span>
              </article>
            ))}
          </div>
          <p className={styles.listNote}>
            Only reports with a backend structuring fixture appear here. Arbitrary prose is not
            accepted yet.
          </p>
        </Panel>

        <Panel
          title="Structured observation preview"
          hint="review before re-planning"
          actions={<ProvenanceBadge provenance="synthetic" />}
        >
          <div className={styles.detailHeader}>
            <div>
              <div className={styles.detailSite}>{selected.site_name}</div>
              <div className={styles.detailMeta}>
                {selected.observer} · {new Date(selected.observed_at).toLocaleString()}
              </div>
            </div>
            <span className={styles.reviewPill}>Manager review</span>
          </div>

          <blockquote className={styles.quote}>{selected.text}</blockquote>

          <div className={styles.extractionGrid}>
            <div className={styles.extractionItem}>
              <span>Site</span>
              <strong>{selected.site_name}</strong>
            </div>
            <div className={styles.extractionItem}>
              <span>Observation type</span>
              <strong>Lesion-pattern tissue loss</strong>
            </div>
            <div className={styles.extractionItem}>
              <span>Context</span>
              <strong>After reported bleaching</strong>
            </div>
            <div className={styles.extractionItem}>
              <span>Provenance</span>
              <strong>Synthetic fixture</strong>
            </div>
          </div>

          <div className={styles.routeTitle}>Evidence routes re-evaluated in parallel</div>
          <div className={styles.routeRow}>
            <span className={styles.routePill}>
              🌡️ Thermal <span>context</span>
            </span>
            <span className={styles.routePill}>
              🦠 Disease <span>lesion signal</span>
            </span>
            <span className={styles.routePill}>
              💧 Runoff <span>independent check</span>
            </span>
            <span className={styles.routePill}>
              ⚓ Physical <span>independent check</span>
            </span>
          </div>

          <p className={styles.note}>{selected.note}</p>
          <Button variant="coral" disabled={submit.isPending} onClick={() => send(selected)}>
            {submit.isPending ? 'Re-planning...' : 'Submit and re-plan'}
          </Button>

          {submit.isError ? (
            <p className={styles.error}>
              <strong>The report was rejected.</strong> {submit.error.message}
              {'detail' in submit.error && submit.error.detail ? ` ${submit.error.detail}` : ''}
            </p>
          ) : null}

          {submit.isSuccess ? (
            <div className={styles.result}>
              <div className={styles.resultTitle}>Report accepted and plan recomputed</div>
              <div className={styles.resultMeta}>
                {submit.data.replan_latency_ms !== null &&
                submit.data.replan_latency_ms !== undefined
                  ? `${submit.data.replan_latency_ms} ms server-side re-plan latency.`
                  : 'Latency was not reported.'}
              </div>
              <div className={styles.resultMeta}>
                {submit.data.plan.assignments.length} site(s) tasked and{' '}
                {(submit.data.plan.deferred ?? []).length} deferred.{' '}
                <Link href="/">Open the updated Command Map</Link>.
              </div>
            </div>
          ) : null}
        </Panel>
      </div>

      <div className={styles.limitation}>
        <span aria-hidden="true">ℹ️</span>
        <span>
          Free text is not implemented in the ingestion lane. This demo uses a clearly labeled
          synthetic fixture and never presents its observation as live field data.
        </span>
      </div>
    </div>
  );
}
