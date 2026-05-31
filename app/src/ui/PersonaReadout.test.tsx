import { describe, expect, it } from '@jest/globals';
import type { ReactElement } from 'react';
import TestRenderer, { act } from 'react-test-renderer';
import type { ReactTestRendererJSON, ReactTestRendererNode } from 'react-test-renderer';

import type { AcousticProfile } from '@/api/types';

import { PersonaReadout } from './PersonaReadout';

type Renderer = ReturnType<typeof TestRenderer.create>;

function render(element: ReactElement): Renderer {
  let tr!: Renderer;
  act(() => {
    tr = TestRenderer.create(element);
  });
  return tr;
}

function textOf(node: ReactTestRendererNode | null): string {
  if (node == null) return '';
  if (typeof node === 'string') return node;
  return ((node as ReactTestRendererJSON).children ?? []).map(textOf).join('');
}

function text(tr: Renderer): string {
  const json = tr.toJSON();
  const nodes = Array.isArray(json) ? json : json ? [json] : [];
  return nodes.map(textOf).join('');
}

const acoustic: AcousticProfile = {
  speech_rate_sps: 4.6,
  articulation_rate_sps: 5.1,
  coverage_ratio: 1.0,
  pause_count: 2,
  pause_total_s: 0.6,
  longest_pause_s: 0.4,
  pitch_range_semitones: 6.0,
  pitch_variation: 2.5,
  energy_variation: 0.4,
  voiced_ratio: 0.7,
  duration_s: 12.3,
  lines_recorded: 3,
  lines_expected: 3,
};

describe('PersonaReadout', () => {
  it('shows the style-match score, the persona name, and the acoustic metrics', () => {
    const tr = render(
      <PersonaReadout
        personaName="Jensen Huang"
        styleMatch={0.81}
        acoustic={acoustic}
        targetBand={[4.2, 5.0]}
      />,
    );
    const rendered = text(tr);
    expect(rendered).toContain('SOUNDED LIKE JENSEN HUANG');
    expect(rendered).toContain('81%');
    expect(rendered).toContain('4.6 syll/s');
    expect(rendered).toContain('2'); // pause count
    expect(rendered).toContain('3/3'); // line coverage
  });

  it('marks the pace in-band with a check when it falls inside the target band', () => {
    const tr = render(
      <PersonaReadout personaName="Jensen Huang" styleMatch={0.81} acoustic={acoustic} targetBand={[4.2, 5.0]} />,
    );
    const rendered = text(tr);
    expect(rendered).toContain('target 4.2');
    expect(rendered).toContain('✓');
  });

  it('shows the band without a check when the pace falls outside it', () => {
    const slow: AcousticProfile = { ...acoustic, speech_rate_sps: 2.2 };
    const tr = render(
      <PersonaReadout personaName="Jensen Huang" styleMatch={0.6} acoustic={slow} targetBand={[4.2, 5.0]} />,
    );
    const rendered = text(tr);
    expect(rendered).toContain('2.2 syll/s');
    expect(rendered).toContain('target 4.2');
    expect(rendered).not.toContain('✓');
  });

  it('omits the target line when the band is unknown', () => {
    const tr = render(
      <PersonaReadout personaName="Steve Jobs" styleMatch={0.7} acoustic={acoustic} targetBand={null} />,
    );
    const rendered = text(tr);
    expect(rendered).toContain('4.6 syll/s');
    expect(rendered).not.toContain('target');
  });

  it('still shows the style-match headline when there is no acoustic profile yet', () => {
    const tr = render(
      <PersonaReadout personaName="Steve Jobs" styleMatch={0.55} acoustic={null} targetBand={[2.8, 3.6]} />,
    );
    const rendered = text(tr);
    expect(rendered).toContain('SOUNDED LIKE STEVE JOBS');
    expect(rendered).toContain('55%');
    expect(rendered).not.toContain('syll/s');
  });

  it('renders an em dash for a missing style-match score', () => {
    const tr = render(
      <PersonaReadout personaName="Steve Jobs" styleMatch={null} acoustic={null} targetBand={null} />,
    );
    expect(text(tr)).toContain('—');
  });
});
