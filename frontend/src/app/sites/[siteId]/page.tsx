import { SiteSummary } from '@/features/evidence/SiteSummary';

/**
 * Site Intelligence for one reef.
 *
 * The four-cause evidence breakdown and the Coordinator's decision are built in
 * step 5. This renders the site's identity and its scores so the map pins have
 * somewhere real to land in the meantime.
 */
export default async function SitePage({ params }: { params: Promise<{ siteId: string }> }) {
  const { siteId } = await params;
  return <SiteSummary siteId={siteId} />;
}
