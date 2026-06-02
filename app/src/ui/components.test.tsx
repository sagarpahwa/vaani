import { describe, it, expect, jest } from '@jest/globals';
import type { ReactElement } from 'react';
import { Text } from 'react-native';
import TestRenderer, { act } from 'react-test-renderer';

import { OptionGroup } from './OptionGroup';
import { ScoreBar } from './ScoreBar';

type Renderer = ReturnType<typeof TestRenderer.create>;
type Instance = ReturnType<Renderer['root']['findAll']>[number];

function render(element: ReactElement): Renderer {
  let tr!: Renderer;
  act(() => {
    tr = TestRenderer.create(element);
  });
  return tr;
}

/** Find pressable chips by their onPress prop (robust to how the RN preset
 *  wraps Pressable, which defeats findAllByType). */
function pressables(tr: Renderer): Instance[] {
  return tr.root.findAll((n: Instance) => typeof n.props?.onPress === 'function');
}

describe('ScoreBar', () => {
  it('renders the label and the formatted percent', () => {
    const tr = render(<ScoreBar label="Clarity" score={0.84} />);
    const texts = tr.root.findAllByType(Text).map((t) => t.props.children);
    expect(texts).toContain('Clarity');
    expect(texts).toContain('84%');
  });
});

describe('OptionGroup', () => {
  it('calls onChange with the pressed option value', () => {
    const onChange = jest.fn<(v: string) => void>();
    const tr = render(
      <OptionGroup
        label="Occasion"
        options={[
          { value: 'a', label: 'A' },
          { value: 'b', label: 'B' },
        ]}
        value="a"
        onChange={onChange}
      />,
    );
    const chips = pressables(tr);
    expect(chips).toHaveLength(2);
    act(() => {
      chips[1].props.onPress();
    });
    expect(onChange).toHaveBeenCalledWith('b');
  });

  it('marks the selected chip via accessibilityState', () => {
    const tr = render(
      <OptionGroup
        label="Style"
        options={[
          { value: 'x', label: 'X' },
          { value: 'y', label: 'Y' },
        ]}
        value="y"
        onChange={() => {}}
      />,
    );
    const selected = pressables(tr).filter((c) => c.props.accessibilityState?.selected);
    expect(selected).toHaveLength(1);
  });
});
