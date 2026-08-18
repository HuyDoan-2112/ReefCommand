'use client';

import Link from 'next/link';
import { useState } from 'react';

import { Button, Panel, StatTile } from '@/components';
import { useStructureObservation, useSubmitStructuredObservation } from '@/hooks/usePlan';
import { cx } from '@/lib/cx';
import type { FieldReport, ReportStructureResult, StructuredObservation } from '@/types';

import styles from './ReportForm.module.css';
import { DEMO_REPORTS, type DemoReport } from './demoReports';

function reportPayload(report: DemoReport): FieldReport {
  return {
    report_id: report.report_id,
    site_id: report.site_id,
    observed_at: report.observed_at,
    observer: report.observer,
    text: report.text,
    image_refs: [],
    provenance: 'synthetic',
    provenance_metadata: null,
  };
}

type SignalCause = 'thermal' | 'disease' | 'runoff' | 'physical';

function primarySignal(observation: StructuredObservation): {
  label: string;
  cause: SignalCause | null;
} {
  if (observation.tissue_loss_observed || observation.lesion_description) {
    return { label: 'Tissue loss / lesion', cause: 'disease' };
  }
  if (observation.broken_coral_observed) {
    return { label: 'Physical breakage', cause: 'physical' };
  }
  if (observation.turbidity_note || observation.sediment_note) {
    return { label: 'Turbidity / runoff', cause: 'runoff' };
  }
  if (observation.bleaching_pct !== null || observation.paling_pct !== null) {
    return { label: 'Bleaching / paling', cause: 'thermal' };
  }
  return { label: 'Mixed / unclear', cause: null };
}

function routeWeight(observation: StructuredObservation, cause: SignalCause): string {
  const signal = primarySignal(observation).cause;
  return signal === cause ? '↑ high weight' : '↓ low weight';
}

function confidencePercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function statusForConfidence(value: number): 'Auto' | 'Review' {
  return value >= 0.8 ? 'Auto' : 'Review';
}

function timeLabel(iso: string): string {
  const minutes = Math.max(0, Math.round((Date.now() - Date.parse(iso)) / 60000));
  return minutes === 0 ? 'just now' : `${minutes} min ago`;
}

interface StructuredHistoryItem {
  report: DemoReport;
  result: ReportStructureResult;
  structuredAt: string;
}

function errorDetail(error: Error): string {
  if ('detail' in error && typeof error.detail === 'string' && error.detail) {
    return error.detail;
  }
  return error.message;
}

export function ReportForm() {
  const [selectedId, setSelectedId] = useState(DEMO_REPORTS[0]!.report_id);
  const [history, setHistory] = useState<StructuredHistoryItem[]>([]);
  const structure = useStructureObservation();
  const submit = useSubmitStructuredObservation();
  const selected =
    DEMO_REPORTS.find((report) => report.report_id === selectedId) ?? DEMO_REPORTS[0]!;
  const payload = reportPayload(selected);
  const extraction = structure.data;
  const observation = extraction?.observation;

  function selectReport(report: DemoReport) {
    setSelectedId(report.report_id);
    structure.reset();
    submit.reset();
  }

  function runExtraction() {
    submit.reset();
    structure.mutate(payload, {
      onSuccess: (result) => {
        setHistory((previous) => [
          {
            report: selected,
            result,
            structuredAt: new Date().toISOString(),
          },
          ...previous.filter((item) => item.report.report_id !== selected.report_id),
        ]);
      },
    });
  }

  function replan() {
    if (!observation) return;
    submit.mutate({ report: payload, observation });
  }

  return (
    <div className={styles.root}>
      <div className={styles.statRow}>
        <StatTile
          label="Reports today"
          value={DEMO_REPORTS.length}
          note="synthetic demo records"
          decoration="📥"
        />
        <StatTile
          label="Auto-structured"
          value={extraction ? '100%' : '0%'}
          note={extraction ? 'by ingestion LLM' : 'waiting for ingestion LLM'}
          decoration="🧩"
        />
        <StatTile
          label="Needs manager review"
          value={extraction ? confidencePercent(1 - extraction.extraction_confidence) : '100%'}
          note={extraction ? 'low confidence extraction' : 'before live extraction'}
          decoration="🚩"
        />
      </div>

      <div className={styles.inboxLayout}>
        <Panel title="Incoming reports" hint="raw text to observation">
          <div className={styles.reportList}>
            {DEMO_REPORTS.map((report) => {
              const active = report.report_id === selected.report_id;
              return (
                <button
                  type="button"
                  key={report.report_id}
                  className={cx(styles.report, active && styles.reportActive)}
                  aria-pressed={active}
                  onClick={() => selectReport(report)}
                >
                  <span className={styles.reportHead}>
                    <span className={styles.reportSite}>{report.site_name}</span>
                    <span className={styles.unreadDot} aria-hidden="true" />
                  </span>
                  <span className={styles.reportMeta}>
                    {report.observer} · {new Date(report.observed_at).toLocaleDateString()}
                  </span>
                  <span className={styles.reportPreview}>{report.text}</span>
                  <span className={styles.reportStatus}>
                    {active ? 'Selected for extraction' : 'Click to inspect'}
                  </span>
                </button>
              );
            })}
          </div>
          <p className={styles.listNote}>
            These records are intentionally informal and have no deterministic extraction fixture.
          </p>
        </Panel>

        <Panel
          title="Structured by Ingestion LLM"
          hint={structure.data ? 'raw text → observation' : 'select a report to begin'}
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

          {!observation || !extraction ? (
            <div className={styles.emptyExtraction}>
              <strong>No structured fields yet</strong>
              <span>
                The backend will send this exact text to the configured LLM and validate the result
                against `StructuredObservation`.
              </span>
              <Button variant="coral" disabled={structure.isPending} onClick={runExtraction}>
                {structure.isPending ? 'Structuring with live LLM...' : 'Structure with live LLM'}
              </Button>
            </div>
          ) : (
            <>
              <div className={styles.runMeta}>
                <strong>
                  {extraction.provider} / {extraction.model}
                </strong>
                <span>{extraction.latency_ms} ms</span>
                <span>{extraction.attempt_count} validated attempt(s)</span>
                {extraction.input_tokens !== null ? (
                  <span>
                    {extraction.input_tokens} in / {extraction.output_tokens ?? 0} out tokens
                  </span>
                ) : null}
              </div>

              <div className={styles.extractionGrid}>
                {[
                  { label: 'Site match', value: selected.site_name },
                  { label: 'Observed condition', value: primarySignal(observation).label },
                  {
                    label: 'Severity vs. baseline',
                    value: observation.compared_to_previous_dive ?? 'Not reported',
                  },
                  {
                    label: 'Extraction confidence',
                    value: `${confidencePercent(extraction.extraction_confidence)} uncalibrated`,
                  },
                  {
                    label: 'Photos attached',
                    value: `${payload.image_refs?.length ?? 0} attached`,
                  },
                  {
                    label: 'Extraction status',
                    value: statusForConfidence(extraction.extraction_confidence),
                  },
                ].map((field) => (
                  <div key={field.label} className={styles.extractionItem}>
                    <span>{field.label}</span>
                    <strong>{field.value}</strong>
                  </div>
                ))}
              </div>

              {observation.extraction_notes ? (
                <div className={styles.extractionNotes}>
                  <strong>Extractor uncertainty</strong>
                  <span>{observation.extraction_notes}</span>
                </div>
              ) : null}

              <div className={styles.routeTitle}>Evidence routes re-evaluated in parallel</div>
              <div className={styles.routeRow}>
                <span className={styles.routePill}>
                  🌡️ Thermal <small>{routeWeight(observation, 'thermal')}</small>
                </span>
                <span className={styles.routePill}>
                  🦠 Disease <small>{routeWeight(observation, 'disease')}</small>
                </span>
                <span className={styles.routePill}>
                  💧 Runoff <small>{routeWeight(observation, 'runoff')}</small>
                </span>
                <span className={styles.routePill}>
                  ⚓ Physical <small>{routeWeight(observation, 'physical')}</small>
                </span>
              </div>

              <p className={styles.note}>{selected.note}</p>
              <div className={styles.actions}>
                <Button variant="ghost" disabled={structure.isPending} onClick={runExtraction}>
                  Run extraction again
                </Button>
                <Button variant="coral" disabled={submit.isPending} onClick={replan}>
                  {submit.isPending ? 'Re-planning...' : 'Use observation and re-plan'}
                </Button>
              </div>
            </>
          )}

          {structure.isError ? (
            <p className={styles.error}>
              <strong>Live structuring failed.</strong> {errorDetail(structure.error)}
            </p>
          ) : null}

          {submit.isError ? (
            <p className={styles.error}>
              <strong>The reviewed observation was rejected.</strong> {errorDetail(submit.error)}
            </p>
          ) : null}

          {submit.isSuccess ? (
            <div className={styles.result}>
              <div className={styles.resultTitle}>Observation accepted and plan recomputed</div>
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

          <section className={styles.recent} aria-labelledby="recently-structured-heading">
            <div className={styles.recentHeader}>
              <h3 id="recently-structured-heading">Recently structured observations</h3>
              <span>
                Confidence is the model&apos;s extraction self-assessment, not a calibrated
                probability
              </span>
            </div>
            {history.length === 0 ? (
              <p className={styles.recentEmpty}>Run the live extractor to populate this history.</p>
            ) : (
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Site</th>
                      <th>Primary signal</th>
                      <th>Confidence</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.slice(0, 5).map((item) => {
                      const signal = primarySignal(item.result.observation);
                      return (
                        <tr key={item.report.report_id}>
                          <td>{timeLabel(item.structuredAt)}</td>
                          <td>{item.report.site_name}</td>
                          <td>{signal.label}</td>
                          <td>{confidencePercent(item.result.extraction_confidence)}</td>
                          <td>
                            <span
                              className={cx(
                                styles.status,
                                statusForConfidence(item.result.extraction_confidence) === 'Auto'
                                  ? styles.statusAuto
                                  : styles.statusReview,
                              )}
                            >
                              {statusForConfidence(item.result.extraction_confidence)}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </Panel>
      </div>

      <div className={styles.limitation}>
        <span aria-hidden="true">ℹ️</span>
        <span>
          The diver notes are synthetic demo inputs. The extraction is a live provider call, is
          schema validated, and remains subject to human review before re-planning.
        </span>
      </div>
    </div>
  );
}
