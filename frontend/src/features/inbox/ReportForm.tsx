'use client';

import { Button, Panel, ProvenanceBadge } from '@/components';
import { useSubmitObservation } from '@/hooks/usePlan';

import styles from './ReportForm.module.css';
import { DEMO_REPORTS, type DemoReport } from './demoReports';

/**
 * Submit a field report. This is the primary re-planning trigger.
 *
 * The backend cannot structure arbitrary prose: the ingestion lane looks up a
 * fixture by `report_id` and rejects anything else with a 422. So this offers
 * the reports that exist rather than a text box that would fail on submit, and
 * says plainly why.
 *
 * The response carries the new plan and the server-measured latency, so the
 * time shown is the pipeline's own rather than one measured across the network.
 */
export function ReportForm() {
  const submit = useSubmitObservation();

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
    <Panel
      title="Field reports"
      hint="submitting one re-runs evidence, policy, the Coordinator and the optimizer"
      actions={
        <ProvenanceBadge
          provenance="synthetic"
          title="Demo field reports are labelled synthetic, not real dive observations"
        />
      }
    >
      <div className={styles.list}>
        {DEMO_REPORTS.map((report) => (
          <article key={report.report_id} className={styles.report}>
            <header className={styles.reportHead}>
              <span className={styles.reportSite}>{report.site_name}</span>
              <span className={styles.reportMeta}>
                {report.observer} &middot; {new Date(report.observed_at).toLocaleDateString()}
              </span>
            </header>
            <blockquote className={styles.quote}>{report.text}</blockquote>
            <p className={styles.note}>{report.note}</p>
            <Button variant="coral" disabled={submit.isPending} onClick={() => send(report)}>
              {submit.isPending ? 'Re-planning...' : 'Submit and re-plan'}
            </Button>
          </article>
        ))}
      </div>

      {submit.isError ? (
        <p className={styles.error}>
          <strong>The report was rejected.</strong> {submit.error.message}
          {'detail' in submit.error && submit.error.detail ? ` ${submit.error.detail}` : ''}
        </p>
      ) : null}

      {submit.isSuccess ? (
        <div className={styles.result}>
          <div className={styles.resultTitle}>Report accepted, plan recomputed</div>
          <div className={styles.resultMeta}>
            {submit.data.replan_latency_ms !== null && submit.data.replan_latency_ms !== undefined
              ? `${submit.data.replan_latency_ms} ms from submission to updated plan, measured server side.`
              : 'Latency was not reported.'}
          </div>
          <div className={styles.resultMeta}>
            {submit.data.plan.assignments.length} site(s) tasked,{' '}
            {(submit.data.plan.deferred ?? []).length} deferred. Trigger{' '}
            <code>{submit.data.plan.replan_trigger}</code>.
          </div>
        </div>
      ) : null}

      <p className={styles.limitation}>
        Free text cannot be submitted yet. The ingestion lane structures a report by looking up a
        fixture, and returns 422 for prose it does not recognise, so a text box here would fail on
        submit rather than be interpreted.
      </p>
    </Panel>
  );
}
