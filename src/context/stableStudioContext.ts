/** Vite can serve timestamped and untimestamped lazy imports in the same tab. */
export function stableStudioContext<T>(hotData: { studioProductDataContext?: T } | undefined, create: () => T): T {
  if (hotData?.studioProductDataContext) return hotData.studioProductDataContext;
  const context = create();
  if (hotData) hotData.studioProductDataContext = context;
  return context;
}
