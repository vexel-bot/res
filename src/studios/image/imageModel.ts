import type {
  AssetRecord,
  StudioDocumentCreate,
  StudioGenerationJobRecord,
} from "../../api/productApi";
import type { CraftDocument } from "../craft/craftApi";
import type { ImageJobInput, ImageOperation } from "./imageApi";

export type ImageMode = "create" | "edit";
export interface ImageDraft {
  title: string;
  prompt: string;
  purpose: string;
  style: string;
  aspect: string;
  additional: string;
  preserve: string;
  brand: boolean;
  audience?: string;
  campaignGoal?: string;
}
export const initialImageDraft = (initial?: {
  title: string;
  objective: string;
}): ImageDraft => ({
  title: initial?.title || "",
  prompt: initial?.objective || "",
  purpose: "Criação livre",
  style: "",
  aspect: "1:1",
  additional: "",
  preserve: "",
  brand: false,
});
export const IMAGE_FORMATS: Array<[string, string]> = [
  ["1:1", "Quadrado · 1:1"],
  ["4:5", "Retrato · 4:5"],
  ["9:16", "Vertical · 9:16"],
  ["16:9", "Horizontal · 16:9"],
];
export const IMAGE_PURPOSES = [
  "Criação livre",
  "Redes sociais",
  "Anúncio",
  "Produto",
  "Institucional",
  "Editorial",
];
export const IMAGE_STYLES = [
  "",
  "Fotografia realista",
  "Editorial",
  "Ilustração",
  "Minimalista",
  "Cinematográfico",
  "3D",
];
const ASPECT_PREFIX = "Enquadramento solicitado: ";
export const imageDimensions = (aspect: string) =>
  ({
    "1:1": [1080, 1080],
    "4:5": [1080, 1350],
    "9:16": [1080, 1920],
    "16:9": [1920, 1080],
  })[aspect] || [1080, 1080];
export function imageDraftFromDocument(doc: CraftDocument): ImageDraft {
  const saved = doc.composition.narrative?.imageStudio as
    Partial<ImageDraft> | undefined;
  const aspect = doc.brief.restrictions
    .find((item) => item.startsWith(ASPECT_PREFIX))
    ?.slice(ASPECT_PREFIX.length);
  return {
    ...initialImageDraft(),
    ...saved,
    ...(aspect && IMAGE_FORMATS.some(([value]) => value === aspect)
      ? { aspect }
      : {}),
    title: doc.title,
    prompt: doc.brief.angle || doc.brief.objective,
    purpose: doc.brief.hook || saved?.purpose || "Criação livre",
    style: doc.brief.tone || "",
    additional: doc.brief.promise || "",
    preserve: doc.brief.restrictions
      .filter((item) => !item.startsWith(ASPECT_PREFIX))
      .join("\n"),
  };
}
export function imageDraftError(draft: ImageDraft) {
  if (draft.prompt.trim().length < 8)
    return "Descreva a imagem ou o ajuste com pelo menos 8 caracteres.";
  if (
    draft.prompt.length > 1000 ||
    draft.additional.length > 1000 ||
    draft.style.length > 1000 ||
    draft.title.length > 180 || (draft.audience?.length || 0) > 2000 || (draft.campaignGoal?.length || 0) > 1000
  )
    return "O texto ultrapassa o limite do briefing salvo. Reduza a descrição ou os ajustes adicionais.";
  const preserve = draft.preserve.split("\n").filter((line) => line.trim());
  if (preserve.length > 30 || preserve.some((line) => line.length > 500))
    return "Use até 30 instruções de preservação, com até 500 caracteres por linha.";
  if (!IMAGE_FORMATS.some(([value]) => value === draft.aspect))
    return "Selecione um enquadramento disponível.";
}
export function imageUploadError(file: Pick<File, "type" | "size">) {
  if (!["image/png", "image/jpeg", "image/webp"].includes(file.type))
    return "Envie uma imagem PNG, JPEG ou WebP.";
  if (!file.size || file.size > 12 * 1024 * 1024)
    return "Use um arquivo de até 12 MB para este fluxo de IA.";
}
export function imagePrompt(draft: ImageDraft, brandContext = "") {
  return [
    draft.prompt.trim(),
    `Finalidade: ${draft.purpose}.`,
    draft.audience?.trim() && `Público: ${draft.audience.trim()}.`,
    draft.campaignGoal?.trim() && `Resultado desejado: ${draft.campaignGoal.trim()}.`,
    draft.style && `Direção visual: ${draft.style}.`,
    `Enquadramento desejado: ${draft.aspect}.`,
    draft.additional.trim(),
    draft.preserve.trim() && `Preservar: ${draft.preserve.trim()}`,
    draft.brand && brandContext
      ? `Contexto autorizado da marca: ${brandContext}`
      : "",
  ]
    .filter(Boolean)
    .join("\n\n");
}
function brief(draft: ImageDraft): StudioDocumentCreate["brief"] {
  return {
    schemaVersion: "studio.creative-brief.v1",
    objective: draft.prompt.trim(),
    audience: draft.audience?.trim() || "Público a definir",
    angle: draft.prompt.trim(),
    hook: draft.purpose,
    promise: draft.additional,
    cta: "",
    channel: "instagram",
    format: "post",
    tone: draft.style,
    restrictions: [
      ASPECT_PREFIX + draft.aspect,
      ...draft.preserve
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean),
    ],
    hypotheses: [],
    evidence: [],
  };
}
export function imageDocumentInput(
  workspaceId: string,
  draft: ImageDraft,
): StudioDocumentCreate {
  const [width, height] = imageDimensions(draft.aspect);
  return {
    workspaceId,
    title:
      draft.title.trim() || draft.prompt.trim().slice(0, 100) || "Nova imagem",
    contentType: "visual",
    brandRevision: 1,
    brief: brief(draft),
    correlationId: crypto.randomUUID(),
    assets: [],
    composition: {
      pages: [
        {
          id: "page-1",
          role: "content",
          width,
          height,
          safeArea: 0,
          background: "#FFFFFF",
          durationMs: null,
          layers: [],
        },
      ],
      tracks: [],
      narrative: { imageStudio: draft },
    },
  };
}
export function updateImageBrief(
  doc: CraftDocument,
  draft: ImageDraft,
): CraftDocument {
  const current = brief(draft);
  return {
    ...doc,
    title: draft.title.trim() || draft.prompt.trim().slice(0, 100) || doc.title,
    brief: {
      ...doc.brief,
      objective: current.objective,
      angle: current.angle,
      hook: current.hook,
      promise: current.promise,
      tone: current.tone,
      restrictions: current.restrictions,
    },
  };
}
/** Preserve every existing/native dependency. Roles organize this UI, not a second library. */
export function imageSourceReferences(
  existing: CraftDocument["assets"],
  sourceId: string | undefined,
  referenceIds: string[],
  assets: AssetRecord[],
): CraftDocument["assets"] {
  const ids = [
    ...new Set([sourceId, ...referenceIds].filter(Boolean) as string[]),
  ];
  const retained = existing.map((ref) => {
    const { imageStudioRole: _role, ...provenance } = ref.provenance || {};
    return { ...ref, provenance };
  });
  for (const id of ids) {
    const asset = assets.find((item) => item.id === id);
    if (!asset?.checksumSha256 || !asset.mediaType?.startsWith("image/"))
      throw new Error(
        "Uma imagem selecionada está indisponível. Confira a Biblioteca antes de salvar.",
      );
    const previous = existing.find((item) => item.id === id);
    const ref = {
      ...(previous || {
        id,
        mediaType: asset.mediaType,
        checksum: asset.checksumSha256,
        origin: asset.metadata?.generationJobId ? "generated" : "workspace",
        rightsStatus: "unknown" as const,
      }),
      provenance: {
        ...(previous?.provenance || asset.metadata || {}),
        imageStudioRole: sourceId === id ? "source" : "reference",
      },
    };
    const index = retained.findIndex((item) => item.id === id);
    if (index < 0) retained.push(ref);
    else retained[index] = ref;
  }
  return retained;
}
export function imageJobInput(
  doc: CraftDocument,
  mode: ImageMode,
  draft: ImageDraft,
  sourceId: string | undefined,
  referenceIds: string[],
  brandContext = "",
): ImageJobInput {
  const error = imageDraftError(draft);
  if (error) throw new Error(error);
  if (mode === "edit" && !sourceId)
    throw new Error("Selecione a imagem original que deseja editar.");
  const references = [...new Set(referenceIds)].filter(
    (id) => mode !== "edit" || id !== sourceId,
  );
  if (references.length > 3)
    throw new Error("Selecione até 3 imagens de referência.");
  const sources = [
    ...new Set([
      ...(mode === "edit" && sourceId ? [sourceId] : []),
      ...references,
    ]),
  ];
  if (
    sources.some(
      (id) =>
        !doc.assets.some(
          (asset) =>
            asset.id === id &&
            asset.mediaType.startsWith("image/") &&
            asset.rightsStatus === "verified" &&
            asset.checksum,
        ),
    )
  )
    throw new Error(
      "Confira a autorização e o vínculo das imagens antes de enviar para a IA.",
    );
  const prompt = imagePrompt(draft, brandContext);
  if (prompt.length > 12000)
    throw new Error(
      "A descrição completa ultrapassa 12.000 caracteres. Reduza os ajustes ou o contexto de marca.",
    );
  return {
    schemaVersion: "studio.editing-ai-request.v1",
    expectedDocumentRevision: doc.revision,
    operation: mode === "edit" ? "edit_image" : "generate_image",
    prompt,
    sourceAssetId: mode === "edit" ? sourceId : undefined,
    referenceAssetIds: references,
    aspectRatio: draft.aspect,
    imageSize: "1K",
    preserve: draft.preserve
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean),
  };
}
export function authorizeImageInputs(
  existing: CraftDocument["assets"],
  ids: string[],
  assets: AssetRecord[],
  confirmed: boolean,
  evidence: string,
  userId: string,
): CraftDocument["assets"] {
  if (!ids.length) return existing;
  if (!confirmed || evidence.trim().length < 3)
    throw new Error(
      "Confirme a autorização e o envio das imagens ao provedor.",
    );
  const next = [...existing];
  let changed = false;
  for (const id of [...new Set(ids)]) {
    const asset = assets.find((item) => item.id === id);
    if (
      !asset?.mediaType?.startsWith("image/") ||
      !asset.checksumSha256 ||
      requiresImageReview(asset)
    )
      throw new Error(
        "Confira o arquivo e sua revisão visual antes de reutilizá-lo.",
      );
    const index = next.findIndex((item) => item.id === id);
    const prior = next[index];
    if (prior?.rightsStatus === "restricted")
      throw new Error(
        "O material selecionado possui uso restrito. Resolva a restrição antes de enviar para a IA.",
      );
    if (
      prior?.rightsStatus === "verified" &&
      prior.checksum === asset.checksumSha256
    )
      continue;
    const ref = {
      id,
      mediaType: asset.mediaType,
      checksum: asset.checksumSha256,
      version: asset.checksumSha256,
      origin: asset.metadata?.generationJobId ? "generated" : "workspace",
      rightsStatus: "verified" as const,
      provenance: {
        ...asset.metadata,
        ...prior?.provenance,
        usageEvidence: evidence.trim(),
        declaredBy: userId,
        declaration:
          "User-confirmed authorization for image generation/editing",
      },
    };
    if (index < 0) next.push(ref);
    else next[index] = ref;
    changed = true;
  }
  return changed ? next : existing;
}
export function imageResultId(
  job?: Pick<StudioGenerationJobRecord, "status" | "result">,
) {
  return job?.status === "succeeded" && typeof job.result?.assetId === "string"
    ? job.result.assetId
    : undefined;
}
export function imageJobOperation(
  job: StudioGenerationJobRecord,
): ImageOperation | undefined {
  const input = job.request?.input as { operation?: string } | undefined;
  return input?.operation === "generate_image" ||
    input?.operation === "edit_image"
    ? input.operation
    : undefined;
}
export function requiresImageReview(asset: AssetRecord) {
  return Boolean(
    asset.metadata?.generationJobId && asset.metadata.visualReview !== "passed",
  );
}
export interface PendingImageRequest {
  documentId: string;
  input: ImageJobInput;
  key: string;
}
export function readPendingImageRequest(
  raw: string | null,
): PendingImageRequest | undefined {
  if (!raw) return;
  try {
    const value = JSON.parse(raw) as PendingImageRequest;
    if (
      typeof value.documentId === "string" &&
      typeof value.key === "string" &&
      /^[A-Za-z0-9._-]{8,160}$/.test(value.key) &&
      ["generate_image", "edit_image"].includes(value.input?.operation) &&
      typeof value.input.prompt === "string" &&
      value.input.prompt.length <= 12000 &&
      Number.isInteger(value.input.expectedDocumentRevision) &&
      value.input.expectedDocumentRevision > 0 &&
      Array.isArray(value.input.referenceAssetIds) &&
      value.input.referenceAssetIds.length <= 3 &&
      value.input.referenceAssetIds.every((id) => typeof id === "string") &&
      Array.isArray(value.input.preserve) &&
      value.input.preserve.length <= 30 &&
      value.input.preserve.every((item) => typeof item === "string") &&
      value.input.schemaVersion === "studio.editing-ai-request.v1" &&
      (value.input.operation !== "edit_image" ||
        typeof value.input.sourceAssetId === "string")
    )
      return value;
  } catch {
    /* Malformed recovery never initiates an external request. */
  }
}
