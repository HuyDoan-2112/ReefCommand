'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type { ReactNode } from 'react';

import { cx } from '@/lib/cx';

import styles from './AppShell.module.css';
import { NAV_ENTRIES, activeEntry } from './navigation';

/**
 * The application frame: sidebar navigation and a sticky topbar.
 *
 * A client component because it reads the current pathname to mark the active
 * nav item. The surfaces it wraps stay server components.
 *
 * The reference's "Ask ReefCommand" input is deliberately not carried over.
 * CLAUDE.md states plainly that this is not a chatbot, and a chat affordance in
 * the topbar would advertise a capability the system does not have and should
 * not claim.
 */

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

        <div className={styles.sidebarFooter} />
      </aside>

      <div className={styles.main}>
        <header className={styles.topbar}>
          <div className={styles.topbarTitleWrap}>
            <h1 className={styles.topbarTitle}>{current?.title ?? 'ReefCommand'}</h1>
            <div className={styles.topbarSub}>{current?.subtitle ?? ''}</div>
          </div>
        </header>
        <div className={styles.content}>{children}</div>
      </div>
    </div>
  );
}
