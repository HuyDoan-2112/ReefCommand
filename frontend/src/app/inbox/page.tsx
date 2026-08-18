import { ReportForm } from '@/features/inbox';
import { CurrentPlan } from '@/features/plan';

/**
 * Report Inbox: submit a field observation and watch the plan change.
 *
 * Composition only.
 */
export default function InboxPage() {
  return (
    <>
      <ReportForm />
      <CurrentPlan />
    </>
  );
}
