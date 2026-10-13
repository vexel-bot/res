/** Invalidates older responses and responses belonging to a different account. */
export function createRequestGuard() {
  let generation = 0;
  return {
    invalidate() { generation += 1; },
    begin(scope: string, currentScope: () => string) {
      const version = ++generation;
      return () => version === generation && scope === currentScope();
    },
  };
}
