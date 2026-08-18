/**
 * The field reports the backend is able to structure.
 *
 * `POST /observations` does not extract structure from arbitrary prose. The
 * ingestion lane looks up a structuring fixture by `report_id` and returns 422
 * for anything it does not recognise:
 *
 *   "no structuring fixture for report '...'; free-text extraction is not
 *    implemented in the ingestion lane"
 *
 * So the inbox offers the reports that do exist rather than a free text box
 * that would fail on submit. The prose below mirrors the backend fixture so the
 * reader can see what is being submitted. If the fixtures change, this list has
 * to change with them, which is why it is a single named constant rather than
 * being scattered through the component.
 */

export interface DemoReport {
  report_id: string;
  site_id: string;
  site_name: string;
  observer: string;
  observed_at: string;
  text: string;
  note: string;
}

export const DEMO_REPORTS: readonly DemoReport[] = [
  {
    report_id: 'cheeca_rocks-2023-09-15-update',
    site_id: 'cheeca_rocks',
    site_name: 'Cheeca Rocks',
    observer: 'Reconstructed demo observer',
    observed_at: '2023-09-15T14:05:00Z',
    text:
      'Went back to Cheeca Rocks. Since the August bleaching, the brain corals and some of the ' +
      'big star corals now have spreading patches of tissue loss, with a sharp line between the ' +
      'living tissue and the bare skeleton.',
    note: 'Adds lesion-pattern tissue loss, which raises disease support and can change the plan.',
  },
] as const;
