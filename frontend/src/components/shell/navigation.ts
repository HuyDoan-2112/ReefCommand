/**
 * The dashboard's four surfaces.
 *
 * The reference switches these with client-side tab state. They are real routes
 * here so a view can be opened directly and a misclick is undone with the back
 * button, which matters during a live presentation. Next.js prefetches each
 * link, so switching stays instant.
 *
 * Titles live beside the hrefs so the topbar and the sidebar cannot disagree
 * about what a surface is called.
 */

export interface NavEntry {
  href: string;
  label: string;
  icon: string;
  section: string;
  title: string;
  subtitle: string;
}

export const NAV_ENTRIES: readonly NavEntry[] = [
  {
    href: '/',
    label: 'Command Map',
    icon: '🗺️',
    section: 'Monitor',
    title: 'Command Map',
    subtitle: 'Current response plan across the Mission: Iconic Reefs sites',
  },
  {
    href: '/inbox',
    label: 'Report Inbox',
    icon: '📥',
    section: 'Monitor',
    title: 'Report Inbox',
    subtitle: 'Field reports, structured into observations that drive re-planning',
  },
  {
    href: '/sites',
    label: 'Site Intelligence',
    icon: '🧭',
    section: 'Decide',
    title: 'Site Intelligence',
    subtitle: 'Cause reasoning behind a single reef, before committing resources',
  },
  {
    href: '/optimizer',
    label: 'Resource Optimizer',
    icon: '🛥️',
    section: 'Decide',
    title: 'Resource Optimizer',
    subtitle: 'Turning limited boats, teams, gear and budget into a ranked plan',
  },
] as const;

/** The nav entry whose route the given path belongs to. */
export function activeEntry(pathname: string): NavEntry | undefined {
  if (pathname === '/') {
    return NAV_ENTRIES[0];
  }
  return NAV_ENTRIES.filter((entry) => entry.href !== '/').find(
    (entry) => pathname === entry.href || pathname.startsWith(`${entry.href}/`),
  );
}
