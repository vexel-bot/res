// A single observer/listener serves all plasma instances, including history avatars.
const instances = new Map<HTMLElement, { inView: boolean; update: (active: boolean) => void }>();
let observer: IntersectionObserver | undefined;
const publish = () => instances.forEach(({ inView, update }) => update(inView && !document.hidden));

export function observePlasma(element: HTMLElement, update: (active: boolean) => void): () => void {
  if (!instances.size) {
    document.addEventListener('visibilitychange', publish);
    if (typeof IntersectionObserver !== 'undefined') observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        const instance = instances.get(entry.target as HTMLElement);
        if (instance) instance.inView = entry.isIntersecting;
      });
      publish();
    });
  }
  instances.set(element, { inView: false, update });
  update(false);
  if (observer) observer.observe(element);
  else { instances.get(element)!.inView = true; publish(); }
  return () => {
    observer?.unobserve(element);
    instances.delete(element);
    if (!instances.size) {
      observer?.disconnect(); observer = undefined;
      document.removeEventListener('visibilitychange', publish);
    }
  };
}
