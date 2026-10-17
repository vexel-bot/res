interface ReadOptions<T> {
  isCurrent: () => boolean;
  read: (signal: AbortSignal) => Promise<T>;
  onStart: () => void;
  onValue: (value: T) => void;
  onError: (error: unknown) => void;
}

// Reads only. Caller context and request order both gate every publication,
// even if a transport ignores cancellation or resolves an old error late.
export function createLatestResourceRead<T>() {
  let sequence = 0;
  let controller: AbortController | undefined;
  const cancel = () => { sequence++; controller?.abort(); controller = undefined; };
  return {
    cancel,
    async load(options: ReadOptions<T>): Promise<void> {
      if (!options.isCurrent()) return;
      cancel();
      const currentSequence = sequence;
      const currentController = new AbortController();
      controller = currentController;
      const current = () => currentSequence === sequence && !currentController.signal.aborted && options.isCurrent();
      options.onStart();
      try {
        const value = await options.read(currentController.signal);
        if (current()) options.onValue(value);
      } catch (error) {
        if (current()) options.onError(error);
      } finally {
        if (currentSequence === sequence) controller = undefined;
      }
    },
  };
}
