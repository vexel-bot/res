export type CopyData = Record<string, string>;
export type SavedCopy = {
  revision: number;
  data: CopyData;
  checks: Record<string, boolean>;
};

export const offerStrategies = {
  product: {
    label: "Produto",
    direction: "Mostre o produto em uso num cenário reconhecível. Escolha um benefício observável e mostre o que muda. Preço, disponibilidade e entrega entram com fonte e condições.",
  },
  service: {
    label: "Serviço",
    direction: "Parta de uma situação específica do cliente. Mostre uma etapa do serviço ou um caso proporcional à promessa. Explique o próximo passo, o escopo e as condições aplicáveis.",
  },
  event: {
    label: "Evento",
    direction: "Dê uma razão concreta para participar. Mostre o que a pessoa vai encontrar e como se inscrever. Data, horário, local, prazo e vagas dependem da fonte.",
  },
};

export const momentStrategies = {
  discovery: {
    label: "Descoberta",
    direction: "Abra com uma situação que o público reconhece. Revele uma mudança concreta e dê tempo para entendê-la antes da oferta.",
  },
  consideration: {
    label: "Consideração",
    direction: "Nomeie a dúvida que trava a decisão. Mostre uma demonstração, um mecanismo ou um caso que responda a essa dúvida.",
  },
  decision: {
    label: "Decisão",
    direction: "Retome a oferta que o público conhece. Explique condições reais e dê um próximo passo simples. Use prazo ou escassez apenas com evidência vigente.",
  },
};

const contextFields = [
  "product", "audience", "problem", "objections", "awareness", "benefit", "offer", "restrictions",
  "cta", "videoChannel", "videoDestination", "videoTiming", "videoEvidence",
] as const;

function owns<T extends object>(map: T, value: string): value is keyof T & string {
  return Object.hasOwn(map, value);
}

export function copyStrategy(data: CopyData) {
  if (!owns(offerStrategies, data.videoKind) || !owns(momentStrategies, data.videoMoment)) return undefined;
  return {
    offerType: data.videoKind,
    audienceMoment: data.videoMoment,
    approach: offerStrategies[data.videoKind].direction,
    opening: momentStrategies[data.videoMoment].direction,
  };
}

function validDate(value: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(value);
  return Number.isFinite(date.valueOf()) && date.toISOString().slice(0, 10) === value;
}

export function copyContext(value: unknown, today = new Date().toISOString().slice(0, 10)) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined;
  const input = value as Record<string, unknown>;
  const keys = [...contextFields, "videoKind", "videoMoment"];
  if (keys.some(key => input[key] !== undefined && (typeof input[key] !== "string" || input[key].length > 2500))) return undefined;
  const data = Object.fromEntries(keys.map(key => [key, String(input[key] ?? "").trim()]));
  const strategy = copyStrategy(data);
  const missing = [
    ...(!strategy ? ["tipo de oferta e momento do público"] : []),
    ...(!data.product ? ["o que é anunciado"] : []),
    ...(!data.audience ? ["público"] : []),
    ...(!data.benefit ? ["benefício"] : []),
    ...(!data.offer ? ["oferta"] : []),
    ...(!data.videoChannel ? ["canal"] : []),
    ...(!data.videoDestination || !data.cta ? ["ação e destino"] : []),
  ];
  const lines = data.videoEvidence.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
  const evidence = lines.flatMap((line, index) => {
    const [claim, source, expiresOn, ...extra] = line.split("|").map(part => part.trim());
    if (!claim || claim.length > 650 || !source || extra.length || (expiresOn && (!validDate(expiresOn) || expiresOn < today))) return [];
    return [{ id: `F${index + 1}`, claim, source, ...(expiresOn ? { expiresOn } : {}) }];
  });
  if (!lines.length) missing.push("uma afirmação confirmada com fonte");
  if (lines.length > 8 || evidence.length !== lines.length) missing.push("revisar o formato e a validade das fontes");
  if (!strategy || missing.length) return { ready: false as const, missing };
  return {
    ready: true as const,
    strategy,
    evidence,
    product: data.product,
    audience: data.audience,
    problem: data.problem,
    objections: data.objections,
    audienceSignals: data.awareness,
    benefit: data.benefit,
    offer: data.offer,
    restrictions: data.restrictions,
    cta: data.cta,
    channel: data.videoChannel,
    destination: data.videoDestination,
    timing: data.videoTiming,
  };
}

export type CopyDraft = {
  angle: string;
  hook: string;
  alternateHook: string;
  body: string;
  hypothesis: string;
};

export function buildCopyHandoff(saved?: SavedCopy) {
  if (!saved) return undefined;
  const { data, revision } = saved;
  const context = copyContext(data);
  if (!context?.ready || !data.angle?.trim() || !data.hook?.trim() || !data.body?.trim()) return undefined;
  return {
    schemaVersion: "clicko.video-ad-copy.v1",
    revision,
    context,
    copy: { angle: data.angle, hook: data.hook, body: data.body, cta: context.cta },
    ...(data.videoAlternateHook && data.videoHypothesis ? {
      experiment: { alternateHook: data.videoAlternateHook, hypothesis: data.videoHypothesis, fixed: "Corpo, oferta, prova e CTA" },
    } : {}),
    direction: [
      "A Clicko preparou o argumento comercial. Você dirige sua realização audiovisual. Transforme a ideia em cenas e decida decupagem, ritmo, pausas, voz, texto em tela, efeitos e som.",
      "Preserve promessa, significado das provas, condições e CTA. Se a realização precisar alterar um desses elementos, proponha o ajuste comercial em separado.",
      "Dê ao público um ponto de partida familiar, mostre a mudança que comprova a ideia e deixe a consequência legível. Verifique se alguém reconhece assunto, benefício e próxima ação na primeira exibição.",
    ],
  };
}
