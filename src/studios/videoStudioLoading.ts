interface SupportResource<T> {
  label: string;
  load: () => Promise<T>;
  commit: (value: T | undefined) => void;
}

// A missing catalogue must remain unavailable, without discarding the project.
export function videoStudioSupportResource<T>(
  resource: SupportResource<T>,
  isCurrent: () => boolean,
  onFailure: (message: string) => void,
): () => Promise<void> {
  return async () => {
    if (!isCurrent()) return;
    try {
      const value = await resource.load();
      if (isCurrent()) resource.commit(value);
    } catch (error) {
      if (!isCurrent()) return;
      resource.commit(undefined);
      onFailure(`${resource.label}: ${error instanceof Error ? error.message : "consulta indisponível"}`);
    }
  };
}

export async function loadVideoStudioResources(options: {
  loadProject: () => Promise<void>;
  support: Array<() => Promise<void>>;
  isCurrent: () => boolean;
  onSupportLoading: (loading: boolean) => void;
}): Promise<void> {
  await options.loadProject();
  if (!options.isCurrent()) return;
  options.onSupportLoading(true);
  // Project readiness does not await these independent, read-only resources.
  void Promise.allSettled(options.support.map(load => Promise.resolve().then(load)))
    .then(() => {
      if (options.isCurrent()) options.onSupportLoading(false);
    });
}
