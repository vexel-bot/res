import type { AssetRecord } from "../../api/productApi";
import { productApi } from "../../api/productApi";
import { craftApi, type CraftCommand, type CraftEngine, type CraftInspection, type NativeEditorStateV1 } from "./craftApi";
import { CraftWorker } from "./craftWorker";

export interface BrowserInspection { layers?: CraftInspection["project"]["layers"]; timeline?: CraftInspection["project"]["timeline"]; fps?: number; [key: string]: unknown }

export const CRAFT_BROWSER_ASSET_LIMIT = 256 * 1024 * 1024;
export const CRAFT_BROWSER_TOTAL_LIMIT = 512 * 1024 * 1024;
export class CraftBrowserCapacityError extends Error {
  constructor() { super("Este projeto usa arquivos grandes. A edição e a prévia serão processadas no servidor."); this.name = "CraftBrowserCapacityError"; }
}

async function verifiedBytes(blob: Blob, checksum?: string) {
  const bytes = new Uint8Array(await blob.arrayBuffer());
  if (checksum) {
    const digest = await crypto.subtle.digest("SHA-256", bytes);
    const actual = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
    if (actual !== checksum.toLowerCase()) throw new Error("O arquivo recebido não corresponde ao checksum do projeto.");
  }
  return bytes;
}

/** All editable local state lives inside the original Rust engine in WASM. */
export class CraftBrowserSession {
  private closed = false;
  private loadedBytes = 0;
  private constructor(private engine: CraftEngine, private adapter: CraftWorker) {}

  static async open(documentId: string, state: NativeEditorStateV1, pageId?: string, signal?: AbortSignal, revision = 0) {
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
    const session = new CraftBrowserSession(state.engine, new CraftWorker(state.engine, documentId, revision));
    const abort = () => session.close();
    signal?.addEventListener("abort", abort, { once: true });
    try {
      await session.adapter.initialize();
      if (state.engine === "photocraft" && !session.adapter.canRegister && state.fontManifest.length) throw new Error("Este projeto usa fontes externas. A prévia será processada no servidor.");
      const capability = await session.request("engine.capabilities", {}) as { buildId?: string; upstreamRevision?: string };
      if (capability.buildId !== state.buildId || capability.upstreamRevision !== state.upstreamRevision) throw new Error("A versão de edição no navegador difere da versão salva. Atualize o Studio.");
      const page = state.pageProjects?.find((item) => item.pageId === pageId) ?? state.pageProjects?.[0];
      const nativeSize = page?.sizeBytes ?? state.sizeBytes;
      if (!Number.isSafeInteger(nativeSize) || nativeSize < 1 || nativeSize > CRAFT_BROWSER_ASSET_LIMIT) throw new CraftBrowserCapacityError();
      session.loadedBytes = nativeSize;
      const manifests = [...state.assetManifest, ...state.fontManifest];
      const materialSizes = new Map<string, number>();
      for (const item of manifests) {
        if (state.engine === "photocraft" && !session.adapter.canRegister) continue;
        const metadata = await craftApi.assetDetails(item.assetId, signal);
        const size = metadata.sizeBytes;
        if (!Number.isSafeInteger(size) || size < 1 || size > CRAFT_BROWSER_ASSET_LIMIT || session.loadedBytes + size > CRAFT_BROWSER_TOTAL_LIMIT) throw new CraftBrowserCapacityError();
        session.loadedBytes += size;
        materialSizes.set(item.assetId, size);
      }
      const blob = await craftApi.loadNative(documentId, signal, false, pageId);
      if (blob.size !== nativeSize) throw new Error("O tamanho do projeto recebido difere do manifesto.");
      await session.adapter.call("open", await verifiedBytes(blob, page?.checksumSha256 ?? state.checksumSha256));
      for (const item of manifests) {
        if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
        if (state.engine === "photocraft" && !session.adapter.canRegister) continue;
        const media = await productApi.studioAssetBlob(item.assetId, signal);
        if (media.size !== materialSizes.get(item.assetId)) throw new Error("O tamanho do material recebido difere do manifesto.");
        const bytes = await verifiedBytes(media, item.checksumSha256);
        await session.adapter.call("register", item.path, bytes);
      }
      return session;
    } catch (cause) { session.close(); throw cause; }
    finally { signal?.removeEventListener("abort", abort); }
  }

  private async request(method: string, params: Record<string, unknown>): Promise<unknown> {
    if (this.closed) throw new Error("A sessão de edição foi encerrada.");
    const requestId = crypto.randomUUID();
    const response = JSON.parse(await this.adapter.call("request", JSON.stringify({ protocolVersion: 1, requestId, engine: this.engine, method, params })) as string) as { protocolVersion: number; requestId: string; result?: unknown; error?: { message?: string } };
    if (response.requestId !== requestId || response.protocolVersion !== 1) throw new Error("A sessão de edição respondeu com um protocolo incompatível.");
    if (response.error) throw new Error(response.error.message || "O motor recusou a alteração.");
    return response.result;
  }

  async inspect(): Promise<BrowserInspection> {
    const result = await this.request("project.inspect", {}) as { inspection?: BrowserInspection } & BrowserInspection;
    return result.inspection ?? result;
  }

  async apply(command: CraftCommand, asset?: AssetRecord): Promise<BrowserInspection> {
    const original = await this.adapter.call("save") as Uint8Array;
    try {
      if (command.id === "asset.import") {
        if (!asset) throw new Error("Escolha o material para inserir.");
        const metadata = typeof asset.sizeBytes === "number" ? asset : await craftApi.assetDetails(asset.id);
        if (!Number.isSafeInteger(metadata.sizeBytes) || metadata.sizeBytes < 1 || metadata.sizeBytes > CRAFT_BROWSER_ASSET_LIMIT || this.loadedBytes + metadata.sizeBytes > CRAFT_BROWSER_TOTAL_LIMIT) throw new CraftBrowserCapacityError();
        const extension: Record<string, string> = { "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "video/mp4": "mp4", "video/webm": "webm", "audio/wav": "wav", "audio/mpeg": "mp3", "audio/flac": "flac" };
        const suffix = extension[asset.mediaType || ""];
        if (!suffix) throw new Error("Este formato ainda não está disponível na edição do navegador.");
        const bytes = await verifiedBytes(await productApi.studioAssetBlob(asset.id), asset.checksumSha256 ?? undefined);
        await this.adapter.call("import", `assets/${asset.id}.${suffix}`, bytes);
        this.loadedBytes += metadata.sizeBytes;
      } else {
        await this.request("engine.execute", { commands: [command] });
      }
      return await this.inspect();
    } catch (cause) { if (!this.closed) await this.adapter.call("open", original); throw cause; }
  }

  async preview(frame: number, fps = 30) {
    const png = await this.adapter.call("preview", frame / Math.max(1, fps), 1600) as Uint8Array;
    return new Blob([new Uint8Array(png)], { type: "image/png" });
  }
  close() { if (!this.closed) { this.closed = true; this.adapter.close(); } }
}
