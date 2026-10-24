export type StudioPane = 'preview' | 'materials' | 'properties' | 'timeline';
export function studioDefaultTimelineHeight(workspace: number) { return workspace < 520 ? 110 : 170; }
export function studioShortcut(key: string, modified: boolean, shift: boolean, typing: boolean) {
  if (!modified) return undefined;
  if (key.toLowerCase() === 's') return 'save';
  if (key.toLowerCase() === 'z' && !typing) return shift ? 'redo' : 'undo';
  return undefined;
}
export function studioWorkspaceHeight(viewport: number, top: number) {
  return Math.max(260, Math.floor(viewport - Math.max(0, top) - 16));
}
export function studioTimelineHeight(value: number, workspace: number) {
  return Math.round(Math.max(100, Math.min(Number.isFinite(value) ? value : 160, 360, workspace * .45)));
}
export function isStudioTypingTarget(target: EventTarget | null) {
  return typeof HTMLElement !== 'undefined' && target instanceof HTMLElement && Boolean(target.closest('input,textarea,select,[contenteditable="true"],[role="combobox"]'));
}
