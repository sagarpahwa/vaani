import { describe, expect, it, jest } from '@jest/globals';
import type { ReactElement } from 'react';
import TestRenderer, { act } from 'react-test-renderer';

import { LineRecorder } from './LineRecorder';

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

function button(tr: Renderer, testID: string): Instance | undefined {
  return pressables(tr).find((n) => n.props.testID === testID);
}

const noop = () => {};

describe('LineRecorder', () => {
  it('offers Record and Skip when idle', () => {
    const onRecord = jest.fn();
    const onSkip = jest.fn();
    const tr = render(
      <LineRecorder
        index={0}
        text="Hello there"
        state="idle"
        onRecord={onRecord}
        onStop={noop}
        onSkip={onSkip}
      />,
    );

    act(() => button(tr, 'record-0')!.props.onPress());
    act(() => button(tr, 'skip-0')!.props.onPress());

    expect(onRecord).toHaveBeenCalledTimes(1);
    expect(onSkip).toHaveBeenCalledTimes(1);
    expect(button(tr, 'stop-0')).toBeUndefined();
  });

  it('shows Stop and a running clock while recording', () => {
    const onStop = jest.fn();
    const tr = render(
      <LineRecorder
        index={0}
        text="Hello there"
        state="recording"
        durationMs={5000}
        onRecord={noop}
        onStop={onStop}
        onSkip={noop}
      />,
    );

    expect(button(tr, 'record-0')).toBeUndefined();
    act(() => button(tr, 'stop-0')!.props.onPress());
    expect(onStop).toHaveBeenCalledTimes(1);
    expect(JSON.stringify(tr.toJSON())).toContain('0:05');
  });

  it('offers Re-record but no Skip once recorded', () => {
    const tr = render(
      <LineRecorder index={2} text="Hello there" state="recorded" onRecord={noop} onStop={noop} onSkip={noop} />,
    );

    expect(button(tr, 'record-2')).toBeDefined();
    expect(button(tr, 'skip-2')).toBeUndefined();
  });
});
