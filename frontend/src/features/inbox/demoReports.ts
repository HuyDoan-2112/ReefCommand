/**
 * Messy synthetic field notes used to demonstrate live LLM structuring.
 * These IDs deliberately have no deterministic structuring fixture.
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
    report_id: 'messy-cheeca-2023-09-15',
    site_id: 'cheeca_rocks',
    site_name: 'Cheeca Rocks',
    observer: 'Demo dive lead',
    observed_at: '2023-09-15T14:05:00Z',
    text:
      'back at cheeca after the aug heat. brain corals + a few big star corals look worse. patches ' +
      'of tissue are gone and the edge is really sharp, live color straight to bare white skeleton. ' +
      'seems to have spread since our last swim but i did not estimate a percent.',
    note: 'Tests lesion morphology, named taxa, progression, and an explicitly missing percentage.',
  },
  {
    report_id: 'messy-looe-2023-09-16',
    site_id: 'looe_key',
    site_name: 'Looe Key',
    observer: 'Demo monitoring diver',
    observed_at: '2023-09-16T10:20:00Z',
    text:
      'looe key visibility was rough today after all that rain. water looked like weak tea on the ' +
      'north side and there was fine brown stuff sitting in low spots. could still see pale coral ' +
      'but no one measured turbidity and i cannot say the rain caused it.',
    note: 'Tests turbidity and sediment extraction without inventing a measurement or causal claim.',
  },
  {
    report_id: 'messy-sombrero-2023-09-17',
    site_id: 'sombrero',
    site_name: 'Sombrero Reef',
    observer: 'Demo survey diver',
    observed_at: '2023-09-17T15:40:00Z',
    text:
      'quick sombrero check after the blow. several branching colonies near the mooring have fresh ' +
      'white snapped ends and loose pieces below them. did not see an anchor or a grounded boat. ' +
      'water itself looked clear.',
    note: 'Tests direct breakage while keeping unreported vessel and storm attribution separate.',
  },
] as const;
