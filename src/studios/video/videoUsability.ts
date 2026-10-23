import type {
  CraftCapability,
  CraftCommand,
  CraftDocument,
  CraftInspection,
  CraftInputSchema,
} from "../craft/craftApi";
import type { VideoArea, VideoClip } from "./videoModel";

export type VideoTool = "clip" | "text" | "audio" | "captions" | "effects";
export function conversionWarnings(
  doc: CraftDocument,
  inspection?: CraftInspection,
) {
  const matching =
    inspection?.documentId === doc.documentId &&
    inspection.revision === doc.revision
      ? inspection
      : undefined;
  return [
    ...new Set([
      ...(doc.nativeEditorState?.migrationWarnings || []),
      ...(matching?.migrationWarnings || []),
      ...(matching?.project.warnings || []),
    ]),
  ];
}
const commonOperations: Record<VideoTool, string[]> = {
  clip: [
    "timeline.trim",
    "timeline.razor",
    "inspector.transform",
    "sequence.settings",
    "asset.import",
  ],
  text: [
    "layer.newText",
    "text.set",
    "text.setStyle",
    "type.create",
    "type.setText",
    "type.setStyle",
  ],
  audio: ["clip.audioGain", "timeline.setTrack", "audio.setVolume"],
  captions: [
    "captions.newTrack",
    "captions.add",
    "captions.setText",
    "captions.setTiming",
    "captions.setStyle",
  ],
  effects: [
    "layer.newShape",
    "effect.add",
    "effects.setParam",
    "prop.addKey",
    "sequence.applyVideoTransition",
    "comp.settings",
  ],
};
export function availableOperations(
  commands: CraftCapability[],
  tool: VideoTool,
) {
  return commands
    .filter(
      (command) => (command as { available?: boolean }).available !== false,
    )
    .filter((command) => !/^(host\.|file\.|engine\.)/.test(command.id))
    .filter((command) =>
      tool === "captions"
        ? /^captions\./.test(command.id)
        : tool === "audio"
          ? /audio|volume|gain|track|voice|sound/i.test(command.id)
          : tool === "text"
            ? /text|type\.|title|font/i.test(command.id)
            : tool === "effects"
              ? /effect|prop\.|key\.|shape|transition|anim|comp\./i.test(
                  command.id,
                )
              : !/caption|audio|voice|file\./i.test(command.id),
    );
}
export function primaryOperations(
  commands: CraftCapability[],
  tool: VideoTool,
) {
  const confirmed = availableOperations(commands, tool);
  return commonOperations[tool].flatMap(
    (id) => confirmed.find((command) => command.id === id) || [],
  );
}
const mainFields = new Set([
  "text",
  "name",
  "color",
  "fill",
  "size",
  "fontSize",
  "font",
  "fontFamily",
  "clip",
  "clips",
  "layer",
  "track",
  "seconds",
  "durationSeconds",
  "assetId",
  "db",
  "edge",
  "deltaFrames",
  "mode",
]);
/** Do not change validation or drop params: this only groups fields in the UI. */
export function operationFields(schema: CraftInputSchema) {
  const entries = Object.entries(schema.properties || {});
  const main = entries.filter(
    ([key, field]) =>
      schema.required?.includes(key) ||
      (mainFields.has(key) &&
        !["object", "array"].includes(String(field.type))),
  );
  return {
    main: { ...schema, properties: Object.fromEntries(main) },
    advanced: {
      ...schema,
      properties: Object.fromEntries(
        entries.filter(([key]) => !main.some(([mainKey]) => mainKey === key)),
      ),
    },
  };
}
export function audioGain(clip: VideoClip, db: number): CraftCommand {
  const id = Number(clip.id);
  if (!Number.isSafeInteger(id) || id < 0)
    throw new Error("Selecione um clipe nativo para ajustar o áudio.");
  if (!Number.isFinite(db) || db < -60 || db > 12)
    throw new Error("Informe um volume entre -60 e +12 dB.");
  return { id: "clip.audioGain", params: { clips: [id], db, mode: "set" } };
}
export function workflowHint(
  area: VideoArea,
  hasProject: boolean,
  nativeReady: boolean,
) {
  if (area === "editor")
    return hasProject
      ? {
          title: nativeReady
            ? "Selecione, ajuste, finalize."
            : "Seu projeto está salvo.",
          text: nativeReady
            ? "Escolha um clipe na timeline. Os ajustes principais ficam no inspetor; as demais ferramentas estão em opções avançadas."
            : "Visualize os materiais originais. A edição da montagem será liberada quando o motor nativo estiver disponível.",
        }
      : {
          title: "Comece com seus materiais.",
          text: "Prepare um projeto ou abra uma produção salva. Não é necessário começar por uma geração com IA.",
        };
  if (area === "motion")
    return {
      title: "Do título à composição.",
      text: "Escolha um preset, personalize a mensagem e salve o projeto. A animação usa keyframes nativos; depois você pode vinculá-la a uma montagem.",
    };
  if (area === "ad")
    return {
      title: "Uma oferta, um caminho claro.",
      text: "Use seu vídeo ou combine mídias da biblioteca. Oferta, público, benefício e chamada acompanham o mesmo projeto até o editor.",
    };
  return {
    title: "Direção primeiro. Montagem depois.",
    text: "Escolha o tipo de vídeo, descreva a mensagem e reúna seus materiais. A IA aplica ajustes no editor quando motor e conexão estiverem disponíveis.",
  };
}
