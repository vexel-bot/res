import type { CraftEngine } from "./craftApi";

/** One native project per dedicated worker; terminating it cancels expensive work. */
export class CraftWorker {
  private worker = new Worker(new URL("./craft.worker.ts", import.meta.url), { type: "module", name: "Clicko Studio" });
  private pending = new Map<string, { resolve: (value: unknown) => void; reject: (cause: Error) => void; timeout: ReturnType<typeof setTimeout> }>();
  private closed = false;
  canRegister = false;
  constructor(private engine: CraftEngine, private projectId: string, private expectedRevision: number) {
    this.worker.onmessage = (event) => {
      const result = event.data;
      const pending = this.pending.get(result.requestId);
      if (!pending) return;
      clearTimeout(pending.timeout); this.pending.delete(result.requestId);
      if (result.protocolVersion !== 1 || result.engine !== this.engine || result.projectId !== this.projectId || result.expectedRevision !== this.expectedRevision) pending.reject(new Error("Resposta de edição incompatível com o projeto."));
      else if (result.error) pending.reject(new Error(result.error));
      else pending.resolve(result.result);
    };
    this.worker.onerror = () => this.close("O processamento local foi interrompido. Reabra o projeto.");
    this.worker.onmessageerror = () => this.close("A sessão local recebeu uma resposta inválida.");
  }
  async initialize() {
    const result = await this.call("initialize") as { canRegister: boolean };
    this.canRegister = result.canRegister;
  }
  call(operation: string, ...args: unknown[]): Promise<unknown> {
    if (this.closed) return Promise.reject(new Error("A sessão de edição foi encerrada."));
    const requestId = crypto.randomUUID();
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => this.close("O processamento local excedeu o limite. Reabra o projeto."), 120000);
      this.pending.set(requestId, { resolve, reject, timeout });
      const transfers = args.filter((value): value is Uint8Array => value instanceof Uint8Array).map((value) => value.buffer as ArrayBuffer);
      this.worker.postMessage({ protocolVersion: 1, requestId, engine: this.engine, projectId: this.projectId, expectedRevision: this.expectedRevision, operation, args }, transfers);
    });
  }
  close(message = "A sessão de edição foi encerrada.") {
    if (this.closed) return;
    this.closed = true; this.worker.terminate();
    for (const pending of this.pending.values()) { clearTimeout(pending.timeout); pending.reject(new Error(message)); }
    this.pending.clear();
  }
}
