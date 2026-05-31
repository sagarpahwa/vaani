import { describe, expect, it } from '@jest/globals';
import type { ReactElement } from 'react';
import { Text } from 'react-native';
import TestRenderer, { act } from 'react-test-renderer';
import type { ReactTestRendererJSON, ReactTestRendererNode } from 'react-test-renderer';

import { CorrectionCard } from './CorrectionCard';

type Renderer = ReturnType<typeof TestRenderer.create>;

function render(element: ReactElement): Renderer {
  let tr!: Renderer;
  act(() => {
    tr = TestRenderer.create(element);
  });
  return tr;
}

/** Flatten all rendered text into one string (interpolated text splits into
 *  multiple string children, so substring checks need the joined form). */
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

describe('CorrectionCard', () => {
  it('renders the 1-based line number, focus capability, both texts, and explanation', () => {
    const tr = render(
      <CorrectionCard
        index={2}
        focusCapability="pace"
        originalText="um so basically"
        correctedText="Here is the key point"
        explanation="Cut the filler and lead with the point."
      />,
    );

    const rendered = text(tr);
    expect(rendered).toContain('Line 3');
    expect(rendered).toContain('Pace');
    expect(rendered).toContain('um so basically');
    expect(rendered).toContain('Here is the key point');
    expect(rendered).toContain('Cut the filler and lead with the point.');
  });

  it('renders the actions slot when provided', () => {
    const tr = render(
      <CorrectionCard
        index={0}
        focusCapability="clarity"
        originalText="o"
        correctedText="c"
        explanation="e"
        actions={<Text>PLAY_SLOT</Text>}
      />,
    );

    expect(text(tr)).toContain('PLAY_SLOT');
  });

  it('omits the explanation block when empty', () => {
    const tr = render(
      <CorrectionCard
        index={0}
        focusCapability="clarity"
        originalText="o"
        correctedText="see this"
        explanation=""
      />,
    );

    const rendered = text(tr);
    expect(rendered).toContain('see this');
    expect(rendered).not.toContain('undefined');
  });
});
