import type { CraftCommand, CraftEngine, CraftInputSchema, CraftInspection } from "./craftApi";

export interface CraftRecovery {
  schemaVersion: "clicko.craft-recovery.v1";
  userId: string;
  workspaceId: string;
  documentId: string;
  engine: CraftEngine;
  expectedRevision: number;
  idempotencyKey: string;
  commands: CraftCommand[];
  attempted?: boolean;
  pageId?: string;
  updatedAt: string;
}

export function craftRecoveryKey(userId: string, workspaceId: string, documentId: string, engine: CraftEngine) {
  return `clicko:craft:v1:${encodeURIComponent(userId)}:${encodeURIComponent(workspaceId)}:${encodeURIComponent(documentId)}:${engine}`;
}

export function readCraftRecovery(value: string | null, scope: Pick<CraftRecovery, "userId" | "workspaceId" | "documentId" | "engine">): CraftRecovery | undefined {
  if (!value) return;
  try {
    const parsed = JSON.parse(value) as CraftRecovery;
    if (parsed.schemaVersion !== "clicko.craft-recovery.v1" || parsed.userId !== scope.userId || parsed.workspaceId !== scope.workspaceId || parsed.documentId !== scope.documentId || parsed.engine !== scope.engine) return;
    if (!Number.isInteger(parsed.expectedRevision) || parsed.expectedRevision < 1 || typeof parsed.idempotencyKey !== "string" || !Array.isArray(parsed.commands)) return;
    if (parsed.commands.some((command) => typeof command.id !== "string" || !command.params || typeof command.params !== "object" || Array.isArray(command.params))) return;
    return parsed.commands.length ? parsed : undefined;
  } catch { return; }
}

export function craftCommands(inspection: CraftInspection | undefined) {
  const caps = inspection?.capabilities;
  return Array.isArray(caps) ? caps : caps?.commands ?? [];
}

export function initialCommandParams(schema: CraftInputSchema, selectedId?: string): Record<string, unknown> {
  return Object.fromEntries(Object.entries(schema.properties ?? {}).flatMap(([key, field]) => {
    if (selectedId && /^(layer|clip|layerId|nodeId|clipId|targetId|selectionId)$/i.test(key)) {
      const numeric = Number(selectedId);
      if (field.type === "integer" || field.type === "number") return Number.isSafeInteger(numeric) ? [[key, numeric]] : [];
      return [[key, selectedId]];
    }
    if (field.default !== undefined) return [[key, field.default]];
    if (schema.required?.includes(key) && field.type === "object" && field.properties) return [[key, initialCommandParams(field, selectedId)]];
    if (schema.required?.includes(key) && field.type === "array" && field.minItems) return [[key, Array.from({ length: field.minItems }, () => field.items?.default ?? (field.items?.type === "number" || field.items?.type === "integer" ? 0 : ""))]];
    return [];
  }));
}

export function commandValidation(schema: CraftInputSchema, params: Record<string, unknown>): string | undefined {
  for (const key of schema.required ?? []) if (params[key] === undefined || params[key] === null || params[key] === "") return `Preencha ${schema.properties?.[key]?.title || key}.`;
  for (const [key, value] of Object.entries(params)) {
    const field = schema.properties?.[key];
    if (!field || value === undefined) continue;
    if (field.enum && !field.enum.includes(value)) return `${field.title || key}: escolha um valor válido.`;
    if (field.type === "string") {
      if (typeof value !== "string") return `${field.title || key}: informe um texto.`;
      if (field.minLength !== undefined && value.length < field.minLength) return `${field.title || key}: texto incompleto.`;
      if (field.maxLength !== undefined && value.length > field.maxLength) return `${field.title || key}: máximo ${field.maxLength} caracteres.`;
    }
    if (field.type === "boolean" && typeof value !== "boolean") return `${field.title || key}: escolha a opção.`;
    if (field.type === "number" || field.type === "integer") {
      if (typeof value !== "number" || !Number.isFinite(value) || (field.type === "integer" && !Number.isInteger(value))) return `${field.title || key}: informe um número válido.`;
      if (field.minimum !== undefined && value < field.minimum) return `${field.title || key}: mínimo ${field.minimum}.`;
      if (field.maximum !== undefined && value > field.maximum) return `${field.title || key}: máximo ${field.maximum}.`;
    }
    if (field.type === "object" && field.properties) {
      if (!value || typeof value !== "object" || Array.isArray(value)) return `${field.title || key}: informe os valores.`;
      const error = commandValidation(field, value as Record<string, unknown>);
      if (error) return error;
    }
    if (field.type === "array") {
      if (!Array.isArray(value)) return `${field.title || key}: selecione os valores.`;
      if (field.minItems !== undefined && value.length < field.minItems) return `${field.title || key}: complete ${field.minItems} valores.`;
      if (field.maxItems !== undefined && value.length > field.maxItems) return `${field.title || key}: máximo ${field.maxItems} valores.`;
      if (field.items?.type === "object" && field.items.properties) {
        for (const item of value) {
          if (!item || typeof item !== "object" || Array.isArray(item)) return `${field.title || key}: complete os valores.`;
          const error = commandValidation(field.items, item as Record<string, unknown>);
          if (error) return error;
        }
      }
    }
  }
}

export function frameCount(inspection?: CraftInspection) {
  const fps = Number(inspection?.project.fps) || 30;
  const duration = Number(inspection?.project.durationMs) || 0;
  return Math.max(0, Math.ceil(duration * fps / 1000) - 1);
}

export function safeCraftMode(mode?: string | null): CraftEngine {
  return mode === "video" ? "filmcraft" : mode === "effects" || mode === "composition" ? "effectcraft" : "photocraft";
}

/** Shared review helper: reading archived canonical text does not invoke an editor. */
export function studioHeadlines(document?: { composition: { pages: Array<{ layers?: Array<{ kind: string; name?: string; properties?: Record<string, unknown> }> }> } }) {
  return document?.composition.pages.map((page) => {
    const layer = page.layers?.find((candidate) => candidate.kind === "text");
    return typeof layer?.properties?.text === "string" && layer.properties.text.trim() ? layer.properties.text : layer?.name || "Sem título";
  }) ?? [];
}
