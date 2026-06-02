import { describe, expect, it, jest } from '@jest/globals';
import type { ReactElement } from 'react';
import TestRenderer, { act } from 'react-test-renderer';

import {
  AUDIENCES,
  DEFAULT_GOAL_FORM,
  DURATIONS,
  OBJECTIVES,
  OCCASIONS,
  STYLES,
  type GoalForm,
} from '@/coaching/goal';

import { GoalSignatureForm } from './GoalSignatureForm';

type Renderer = ReturnType<typeof TestRenderer.create>;
type Instance = ReturnType<Renderer['root']['findAll']>[number];

function render(element: ReactElement): Renderer {
  let tr!: Renderer;
  act(() => {
    tr = TestRenderer.create(element);
  });
  return tr;
}

function pressables(tr: Renderer): Instance[] {
  return tr.root.findAll((n: Instance) => typeof n.props?.onPress === 'function');
}

describe('GoalSignatureForm', () => {
  it('renders one chip per option across all five groups', () => {
    const tr = render(<GoalSignatureForm value={DEFAULT_GOAL_FORM} onChange={() => {}} />);
    expect(pressables(tr)).toHaveLength(
      OBJECTIVES.length + OCCASIONS.length + AUDIENCES.length + STYLES.length + DURATIONS.length,
    );
  });

  it('edits only the objective field when an objective chip is pressed', () => {
    const onChange = jest.fn<(f: GoalForm) => void>();
    const tr = render(<GoalSignatureForm value={DEFAULT_GOAL_FORM} onChange={onChange} />);
    // Objective is the first group, so its chips lead the flat list.
    act(() => {
      pressables(tr)[1].props.onPress();
    });
    expect(onChange).toHaveBeenCalledWith({
      ...DEFAULT_GOAL_FORM,
      objective: OBJECTIVES[1].value,
    });
  });
});
