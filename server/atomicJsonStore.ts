import { closeSync, copyFileSync, existsSync, fsyncSync, mkdirSync, openSync, readFileSync, renameSync, statSync, unlinkSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { randomUUID } from 'node:crypto';

/** Local, single-server persistence. Conflicting writers fail instead of losing data. */
export class AtomicJsonStore<T> {
  private lastSaved: string | null = null;
  readonly filename: string;

  constructor(filename: string, private validate: (value: unknown) => value is T) {
    this.filename = path.resolve(filename);
  }

  private read(): string | null {
    try {
      if (statSync(this.filename).size > 50 * 1024 * 1024) throw new Error('GOVERNANCE_STORE_TOO_LARGE');
      return readFileSync(this.filename, 'utf8');
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') return null;
      throw error;
    }
  }

  load(initial: T): T {
    const raw = this.read();
    if (raw === null) {
      this.lastSaved = null;
      this.save(initial);
      return structuredClone(initial);
    }
    let data: unknown;
    try { data = JSON.parse(raw); } catch { throw new Error('GOVERNANCE_STORE_INVALID_JSON'); }
    if (!this.validate(data)) throw new Error('GOVERNANCE_STORE_INVALID_SCHEMA');
    this.lastSaved = raw;
    return data;
  }

  save(value: T): void {
    if (!this.validate(value)) throw new Error('GOVERNANCE_STORE_INVALID_SCHEMA');
    const next = JSON.stringify(value);
    if (Buffer.byteLength(next, 'utf8') > 50 * 1024 * 1024) throw new Error('GOVERNANCE_STORE_TOO_LARGE');
    if (next === this.lastSaved) return;
    mkdirSync(path.dirname(this.filename), { recursive: true, mode: 0o700 });
    const lock = `${this.filename}.lock`;
    const temporary = `${this.filename}.${randomUUID()}.tmp`;
    // wx prevents concurrent writers. A stale crash lock requires operator inspection.
    const lockFd = openSync(lock, 'wx', 0o600);
    let tempFd: number | undefined;
    let temporaryCreated = false;
    try {
      writeFileSync(lockFd, String(process.pid));
      if (this.read() !== this.lastSaved) throw new Error('GOVERNANCE_STORE_CONFLICT');
      tempFd = openSync(temporary, 'wx', 0o600);
      temporaryCreated = true;
      writeFileSync(tempFd, next, 'utf8');
      fsyncSync(tempFd);
      closeSync(tempFd); tempFd = undefined;
      if (this.lastSaved !== null) copyFileSync(this.filename, `${this.filename}.previous`);
      renameSync(temporary, this.filename);
      temporaryCreated = false;
      this.lastSaved = next;
    } finally {
      // Cleanup cannot undo a committed rename or turn a successful save into
      // an API rollback. An unreleased lock makes the next write fail safely.
      const cleanup = (action: () => void) => {
        try { action(); } catch { console.warn('Governance storage cleanup requires operator inspection.'); }
      };
      if (tempFd !== undefined) cleanup(() => closeSync(tempFd));
      if (temporaryCreated && existsSync(temporary)) cleanup(() => unlinkSync(temporary));
      cleanup(() => closeSync(lockFd));
      cleanup(() => unlinkSync(lock));
    }
  }
}
