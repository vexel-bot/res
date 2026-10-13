export type KlicPlasmaState = 'idle' | 'connecting' | 'listening' | 'processing' | 'speaking' | 'error';
export type KlicPlasmaActivity = KlicPlasmaState | 'interacting' | 'responding';

export function plasmaEnergy(value: number): number {
  return Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 0;
}

// Presentation only: never starts requests, recording or playback.
export function plasmaActivity(state: KlicPlasmaState, responding = false, interacting = false): KlicPlasmaActivity {
  if (state === 'error' || state === 'listening' || state === 'speaking' || state === 'connecting') return state;
  if (state === 'processing') return responding ? 'responding' : 'processing';
  return interacting ? 'interacting' : 'idle';
}

export function plasmaCompleted(previous: KlicPlasmaActivity, next: KlicPlasmaActivity, previousId?: string, nextId?: string): boolean {
  return (previous === 'processing' || previous === 'responding' || previous === 'speaking')
    && next !== 'error' && next !== 'connecting' && Boolean(nextId) && previousId !== nextId;
}
