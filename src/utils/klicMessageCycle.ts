export const KLIC_MESSAGE_INTERVAL = 60_000;
export const KLIC_MESSAGE_VISIBLE_TIME = 15_000;

type CycleOptions = {
  schedule: (callback: () => void, delay: number) => number;
  cancel: (timer: number) => void;
  show: () => void;
  hide: () => void;
  clear: () => void;
  canShow: () => boolean;
  entryDuration: () => number;
  exitDuration: () => number;
};

/** A single chained timeout; waiting starts only after the exit completes. */
export function startKlicMessageCycle(options: CycleOptions) {
  let timer: number | undefined;
  let stopped = false;
  const after = (delay: number, callback: () => void) => {
    if (stopped) return;
    timer = options.schedule(() => {
      timer = undefined;
      if (!stopped) callback();
    }, delay);
  };
  const wait = () => after(KLIC_MESSAGE_INTERVAL, () => {
    if (!options.canShow()) { wait(); return; }
    options.show();
    after(options.entryDuration() + KLIC_MESSAGE_VISIBLE_TIME, () => {
      options.hide();
      after(options.exitDuration(), () => {
        options.clear();
        wait();
      });
    });
  });
  wait();
  return () => {
    stopped = true;
    if (timer !== undefined) options.cancel(timer);
  };
}
