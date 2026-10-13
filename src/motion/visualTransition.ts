import { flushSync } from 'react-dom';

type TransitionKind = 'theme' | 'content';
type SnapshotTransition = {
  skipTransition: () => void;
  ready: Promise<unknown>;
  finished: Promise<unknown>;
};
type TransitionHost = {
  enabled: () => boolean;
  start: (update: () => void) => SnapshotTransition;
  mark: (kind?: TransitionKind) => void;
  commit: (update: () => void) => void;
};

/** Only discrete presentation changes belong here, never requests or form edits. */
export function createVisualTransitionRunner(host: TransitionHost) {
  let active: { finishUpdate: () => void; transition?: SnapshotTransition } | undefined;

  return (kind: TransitionKind, update: () => void) => {
    // Skipping a browser animation does not cancel its queued update callback.
    // Commit it once before the next update so rapid clicks cannot restore stale UI.
    if (active) {
      active.finishUpdate();
      active.transition?.skipTransition();
      active = undefined;
      host.mark();
    }
    if (!host.enabled()) {
      update();
      return;
    }
    let committed = false;
    const entry = {
      finishUpdate: () => {
        if (committed) return;
        committed = true;
        host.commit(update);
      },
      transition: undefined as SnapshotTransition | undefined,
    };
    active = entry;
    host.mark(kind);
    const clear = () => {
      if (active !== entry) return;
      active = undefined;
      host.mark();
    };
    try {
      entry.transition = host.start(entry.finishUpdate);
      // A skipped/unsupported snapshot must never produce an unhandled rejection.
      void entry.transition.ready.catch(() => {});
      void entry.transition.finished.then(clear, clear);
    } catch {
      clear();
      entry.finishUpdate();
    }
  };
}

export const visualTransition = createVisualTransitionRunner({
  enabled: () => typeof document !== 'undefined'
    && typeof document.startViewTransition === 'function'
    && document.visibilityState === 'visible'
    && !window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  start: update => document.startViewTransition(update),
  mark: kind => {
    if (kind) document.documentElement.dataset.clickoTransition = kind;
    else delete document.documentElement.dataset.clickoTransition;
  },
  commit: update => flushSync(update),
});
