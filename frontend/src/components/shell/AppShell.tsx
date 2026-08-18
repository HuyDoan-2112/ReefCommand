'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type { ReactNode } from 'react';

import { ProvenanceBadge } from '@/components/ProvenanceBadge';
import { useScenario } from '@/hooks/useResources';
import { cx } from '@/lib/cx';

import styles from './AppShell.module.css';
import { NAV_ENTRIES, activeEntry } from './navigation';

/**
 * The application frame: sidebar navigation and a sticky topbar.
 *
 * A client component because it reads the current pathname to mark the active
 * nav item. The surfaces it wraps stay server components.
 *
 * The reference's chat-shaped topbar control is used as a read-only workspace
 * status pill. ReefCommand is decision support, not a chatbot, so the visual
 * shape is preserved without advertising an unsupported capability.
 */

function ResourceMini() {
  const { data: view } = useScenario();

  if (!view) {
    return <div className={styles.resourceMini}>Loading simulated capacity...</div>;
  }

  const scenario = view.scenario;
  const boatsAvailable = scenario.boats.filter((boat) => boat.available !== false).length;
  const boatPercent = Math.round((boatsAvailable / Math.max(scenario.boats.length, 1)) * 100);
  const teamHours = scenario.dive_teams.reduce((sum, team) => sum + team.available_hours, 0);
  const teamPercent = Math.min(
    100,
    Math.round((teamHours / Math.max(scenario.daylight_hours * 3, 1)) * 100),
  );

  return (
    <>
      <div className={styles.resourceTitle}>Simulated resources</div>
      <div className={styles.miniBarRow}>
        <span className={styles.miniLabel}>Boats</span>
        <span className={styles.miniBarTrack}>
          <span className={styles.miniBarFill} style={{ width: `${boatPercent}%` }} />
        </span>
        <span className={styles.miniValue}>{boatsAvailable}</span>
      </div>
      <div className={styles.miniBarRow}>
        <span className={styles.miniLabel}>Teams</span>
        <span className={styles.miniBarTrack}>
          <span className={styles.miniBarFill} style={{ width: `${teamPercent}%` }} />
        </span>
        <span className={styles.miniValue}>{scenario.dive_teams.length}</span>
      </div>
      <div className={styles.miniBarRow}>
        <span className={styles.miniLabel}>Budget</span>
        <span className={styles.miniBarTrack}>
          <span className={styles.miniBarFill} style={{ width: '100%' }} />
        </span>
        <span className={styles.miniValue}>${Math.round(scenario.budget_usd / 1000)}k</span>
      </div>
      <div className={styles.workspaceChip}>
        <div className={styles.avatar} aria-hidden="true">
          FK
        </div>
        <div>
          <div className={styles.workspaceName}>Florida Keys</div>
          <div className={styles.workspaceRole}>Response workspace</div>
        </div>
      </div>
    </>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const current = activeEntry(pathname);
  const sections = [...new Set(NAV_ENTRIES.map((entry) => entry.section))];

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <div className={styles.brandMark} aria-hidden="true">
            🪸
          </div>
          <div>
            <div className={styles.brandName}>ReefCommand</div>
            <div className={styles.brandTag}>Decision support</div>
          </div>
        </div>

        <nav className={styles.nav} aria-label="Dashboard surfaces">
          {sections.map((section) => (
            <div key={section}>
              <div className={styles.navSectionLabel}>{section}</div>
              {NAV_ENTRIES.filter((entry) => entry.section === section).map((entry) => {
                const isActive = current?.href === entry.href;
                return (
                  <Link
                    key={entry.href}
                    href={entry.href}
                    className={cx(styles.navItem, isActive && styles.navItemActive)}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    <span className={styles.navIcon} aria-hidden="true">
                      {entry.icon}
                    </span>
                    {entry.label}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        <div className={styles.sidebarFooter}>
          <ResourceMini />
        </div>
      </aside>

      <div className={styles.main}>
        <header className={styles.topbar}>
          <div className={styles.topbarTitleWrap}>
            <h1 className={styles.topbarTitle}>{current?.title ?? 'ReefCommand'}</h1>
            <div className={styles.topbarSub}>{current?.subtitle ?? ''}</div>
          </div>
          <div className={styles.workspaceStatus} aria-label="Current workspace status">
            <span aria-hidden="true">🌊</span>
            <span className={styles.workspaceStatusText}>Florida Keys response workspace</span>
            <span className={styles.workspaceStatusTag}>Current plan</span>
          </div>
          <div className={styles.statusIcon} title="Data provenance is shown on every surface">
            <ProvenanceBadge provenance="simulated" />
          </div>
        </header>
        <div className={styles.content}>{children}</div>
      </div>
    </div>
  );
}
