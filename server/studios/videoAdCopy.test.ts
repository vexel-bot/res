import assert from "node:assert/strict";
import test from "node:test";
import { buildCopyHandoff, copyContext, copyStrategy } from "../../src/studios/video/adCopy";
import { parseVideoCopy } from "./videoAdCopy";

const data = {
  videoKind: "event",
  videoMoment: "decision",
  product: "Oficina de cerâmica",
  audience: "Quem pediu detalhes da oficina",
  benefit: "Praticar a técnica com orientação",
  offer: "Inscrição para turma presencial",
  videoChannel: "Instagram",
  videoDestination: "Página de inscrição",
  videoEvidence: "Materiais incluídos para inscritos | Programa da oficina | 2099-12-01",
  cta: "Confira as condições na página de inscrição",
  restrictions: "Apenas para inscritos",
};

test("a estratégia diferencia tipo de oferta e momento e exclui fontes fora da validade", () => {
  assert.equal(copyStrategy(data)?.offerType, "event");
  assert.match(copyStrategy(data)!.opening, /Retome a oferta/);
  assert.match(copyStrategy({ ...data, videoKind: "service", videoMoment: "discovery" })!.approach, /etapa do serviço/);
  assert.equal(copyStrategy({ ...data, videoKind: "constructor" }), undefined);
  assert.equal(copyContext(data, "2099-12-01")?.ready, true);
  assert.equal(copyContext(data, "2099-12-02")?.ready, false);
  assert.equal(copyContext({ ...data, videoEvidence: "Vagas limitadas" })?.ready, false);
  assert.equal(copyContext({ ...data, videoEvidence: "Existem vagas | Folheto | 2099-02-29" })?.ready, false);
});

test("a geração usa a evidência registrada por inteiro e limita a variação ao gancho", () => {
  const context = copyContext(data, "2099-12-01");
  assert.ok(context?.ready);
  const raw = {
    angle: "Da dúvida sobre materiais ao primeiro exercício",
    hook: "Preciso levar argila?",
    alternateHook: "Já pensou em sair da primeira aula com uma peça?",
    body: "[[F1]]. Você pratica o primeiro exercício com orientação.",
    hypothesis: "Comparar objeção e visualização do resultado",
  };
  const draft = parseVideoCopy(JSON.stringify(raw), context);
  assert.match(draft.body, /^Materiais incluídos para inscritos/);
  for (const invalid of [
    { ...raw, body: 'Texto sem fonte' },
    { ...raw, body: '[[F30]]' },
    { ...raw, body: '[[F1]] [[F1]]' },
    { ...raw, alternateHook: 'preciso levar argila!' },
  ]) {
    assert.throws(() => parseVideoCopy(JSON.stringify(invalid), context));
  }
  const saved = { revision: 2, checks: {}, data: { ...data, ...draft, videoAlternateHook: draft.alternateHook, videoHypothesis: draft.hypothesis } };
  const exported = buildCopyHandoff(saved);
  assert.equal(exported?.revision, 2);
  assert.equal(exported?.copy.cta, data.cta);
  assert.equal(exported?.context.restrictions, data.restrictions);
  assert.equal(exported?.context.evidence[0].source, "Programa da oficina");
  assert.equal(exported?.experiment?.alternateHook, raw.alternateHook);
  assert.equal(buildCopyHandoff({ ...saved, data: { ...saved.data, cta: "" } }), undefined);
});
