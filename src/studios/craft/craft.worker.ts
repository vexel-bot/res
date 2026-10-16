import type { CraftEngine } from "./craftApi";

interface NativeAdapter {
  request(json: string): string;
  openNative(bytes: Uint8Array): void;
  saveNative(): Uint8Array;
  previewPng(time: number, maxSide?: number): Uint8Array;
  importAsset(path: string, bytes: Uint8Array): string;
  registerAsset?(path: string, bytes: Uint8Array): void;
}
interface Message {
  protocolVersion: 1; requestId: string; projectId: string; engine: CraftEngine; expectedRevision: number;
  operation: "initialize" | "request" | "open" | "save" | "preview" | "register" | "import";
  args: unknown[];
}
const scope = self as unknown as { onmessage: (event: MessageEvent<Message>) => void; postMessage: (message: unknown, transfer?: Transferable[]) => void; location: Location };
let adapter: NativeAdapter | undefined;
let identity: Pick<Message, "projectId" | "engine" | "expectedRevision"> | undefined;
let queue = Promise.resolve();

scope.onmessage = (event) => {
  const message = event.data;
  queue = queue.then(async () => {
    const envelope = { protocolVersion: 1, requestId: message.requestId, projectId: message.projectId,
      engine: message.engine, expectedRevision: message.expectedRevision };
    try {
      if (message.protocolVersion !== 1 || !["photocraft", "filmcraft", "effectcraft"].includes(message.engine)) throw new Error("Protocolo de edição incompatível.");
      let result: unknown;
      if (message.operation === "initialize") {
        if (adapter) throw new Error("A sessão já foi iniciada.");
        identity = envelope;
        const url = new URL(`/craft/${message.engine}/clicko_${message.engine}_adapter.js`, scope.location.origin).href;
        const module = await import(/* @vite-ignore */ url);
        await module.default();
        adapter = new module.Adapter();
        result = { canRegister: Boolean(adapter.registerAsset) };
      } else {
        if (!adapter || !identity || identity.projectId !== message.projectId || identity.engine !== message.engine || identity.expectedRevision !== message.expectedRevision) throw new Error("O projeto ou a revisão da sessão mudou.");
        const args = message.args;
        switch (message.operation) {
          case "request": result = adapter.request(String(args[0])); break;
          case "open": adapter.openNative(args[0] as Uint8Array); break;
          case "save": result = new Uint8Array(adapter.saveNative()); break;
          case "preview": result = new Uint8Array(message.engine === "photocraft"
            ? adapter.previewPng(Number(args[1])) : adapter.previewPng(Number(args[0]), Number(args[1]))); break;
          case "register":
            if (!adapter.registerAsset) throw new Error("Este motor não registra materiais externos no navegador.");
            adapter.registerAsset(String(args[0]), args[1] as Uint8Array); break;
          case "import": result = adapter.importAsset(String(args[0]), args[1] as Uint8Array); break;
          default: throw new Error("Operação de edição desconhecida.");
        }
      }
      scope.postMessage({ ...envelope, result }, result instanceof Uint8Array ? [result.buffer as ArrayBuffer] : []);
    } catch (cause) { scope.postMessage({ ...envelope, error: cause instanceof Error ? cause.message : String(cause) }); }
  });
};
