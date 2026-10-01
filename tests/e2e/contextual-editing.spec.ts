import { expect, test, type Page } from "@playwright/test";
import path from "node:path";

async function openQualityHarness(page: Page, record: unknown) {
  await page.route("**/__quality-test-host", route => route.fulfill({ contentType: "text/html", body: `
    <!doctype html><html><head><script type="module">
    import RefreshRuntime from '/@react-refresh';
    RefreshRuntime.injectIntoGlobalHook(window);
    window.$RefreshReg$ = () => {};
    window.$RefreshSig$ = () => type => type;
    window.__vite_plugin_react_preamble_installed__ = true;
    </script></head><body></body></html>` }));
  await page.goto("/__quality-test-host", { waitUntil: "domcontentloaded" });
  await page.waitForFunction(() => (window as any).__vite_plugin_react_preamble_installed__ === true);
  await page.evaluate(async value => {
    const modulePath = "/tests/fixtures/contextual-editing-harness.tsx";
    const { mountContextualHarness } = await import(modulePath);
    (window as any).__contextualHarness = mountContextualHarness(value);
  }, record);
}

test("experimental Studio indicator stays pending and phase request is audiovisual", async ({ page }) => {
  const doc = { documentId: "quality-doc", workspaceId: "workspace", revision: 1, version: 1,
    brief: { objective: "Mostrar o produto" }, assets: [],
    composition: { pages: [{ id: "page", width: 1080, height: 1920 }], narrative: {} } };
  let submitted: any;
  await page.route("**/api/v1/studios/v1/editing/ai", r => r.fulfill({ json: {
    operations: ["plan"], label: "Gemini", qualityIndicatorEnabled: true,
    remotionNative: { configured: true }, contextualV2: { configured: true },
  } }));
  await page.route("**/api/v1/studios/v1/workspaces/workspace/visual-quality", r => r.fulfill({ json: {
    baseline: { visualStatus: "rejected", humanScores: null, limitations: [], renders: [] },
    targetBriefs: 3, phaseStatus: "pending",
    budget: { limitUsd: 10, committedOrReservedUsd: 0, attempts: 0, remainingUsd: 10 },
    progress: { distinctBriefs: 1, materialsReady: 0, rendered: 0, visualApproved: 0, comparisonPassed: 0 },
    cases: [{ documentId: "quality-doc", title: "Produto", materials: { status: "pending",
      blockers: ["two_distinct_action_sources_required"] }, renderStatus: "pending",
      visualStatus: "pending", comparisonStatus: "pending" }], renders: [],
  } }));
  await page.route("**/api/v1/studios/v1/transcripts?*", r => r.fulfill({ json: [] }));
  await page.route("**/api/v1/studios/v1/editing/repertoire?*", r => r.fulfill({ json: { techniques: [] } }));
  await page.route("**/editing-plans/latest", r => r.fulfill({ json: null }));
  await page.route("**/production-runs", r => {
    submitted = r.request().postDataJSON();
    return r.fulfill({ json: { id: "phase-run", revision: 1, status: "blocked", stage: "direction",
      blockers: ["visual_quality_materials_pending"], artifacts: {} } });
  });
  await openQualityHarness(page, doc);
  await expect(page.getByRole("heading", { name: "Qualidade visual · fase experimental" })).toBeVisible();
  await expect(page.getByText("Fase: pendente de evidência.")).toBeVisible();
  await page.getByLabel("Validar nesta fase: 15 s, montagem híbrida, áudio e teto compartilhado de US$ 10").check();
  await page.getByLabel("Roteiro e informações de origem").fill("Mostrar o produto em uso.");
  await page.getByRole("button", { name: "Desenvolver montagem mista" }).click();
  await expect.poll(() => submitted?.qualityPhaseId).toBe("visual-quality-2026-10-01");
  expect(submitted.durationSeconds).toBe(15);
  expect(submitted.evaluationScope).toBe("audiovisual");
  expect(submitted.nativeSceneEditing).toBe(true);
});

test("comparison in Studio hides roles during playback and records bound preference", async ({ page }) => {
  const checksum = (letter: string) => letter.repeat(64);
  const doc = { documentId: "comparison-doc", workspaceId: "workspace", revision: 2, version: 1,
    brief: { objective: "Comparar montagem" }, assets: [
      { id: "source-1", mediaType: "video/mp4", checksum: checksum("1"), rightsStatus: "verified" },
      { id: "source-2", mediaType: "video/mp4", checksum: checksum("2"), rightsStatus: "verified" },
      { id: "control", mediaType: "video/mp4", checksum: checksum("c"), rightsStatus: "verified" },
    ], composition: { pages: [{ id: "page", width: 1080, height: 1920 }], narrative: {} } };
  let submitted: any;
  await page.route("**/api/v1/studios/v1/editing/ai", r => r.fulfill({ json: {
    operations: [], label: "Local", qualityIndicatorEnabled: true } }));
  await page.route("**/api/v1/studios/v1/workspaces/workspace/visual-quality", r => r.fulfill({ json: {
    baseline: { visualStatus: "rejected", humanScores: null, limitations: [], renders: [] },
    targetBriefs: 3, phaseStatus: "pending",
    budget: { limitUsd: 10, committedOrReservedUsd: 0, attempts: 0, remainingUsd: 10 },
    progress: { distinctBriefs: 1, materialsReady: 0, rendered: 0, visualApproved: 0, comparisonPassed: 0 },
    cases: [], renders: ["a", "b"].map(letter => ({ runId: `edit-${letter}`, documentId: "comparison-doc",
      documentRevision: 2, assetId: `render-${letter}`, qualityPhaseId: "visual-quality-2026-10-01",
      renderChecksum: checksum(letter), technicalStatus: "passed", visualStatus: "approved",
      autonomyStatus: "partial", recordedManualInterventions: 0, blockers: [], findings: [] })),
  } }));
  await page.route("**/api/v1/studios/v1/transcripts?*", r => r.fulfill({ json: [] }));
  await page.route("**/api/v1/studios/v1/editing/repertoire?*", r => r.fulfill({ json: { techniques: [] } }));
  await page.route("**/editing-plans/latest", r => r.fulfill({ json: null }));
  const fixture = path.resolve("output/editorial-operations-20260930/bebida/animatic-A.mp4");
  await page.route("**/api/v1/assets/*/content", r => r.fulfill({ path: fixture, contentType: "video/mp4" }));
  await page.route("**/visual-quality-comparison", r => {
    submitted = r.request().postDataJSON();
    return r.fulfill({ json: { status: "pending" } });
  });
  await openQualityHarness(page, doc);
  await page.getByText("Comparar duas montagens e a concatenação de controle").click();
  await page.getByLabel("Montagem A").selectOption("edit-a");
  await page.getByLabel("Montagem B").selectOption("edit-b");
  await page.getByLabel("Concatenação de controle").selectOption("control");
  await page.getByLabel("Fonte 1").selectOption("source-1");
  await page.getByLabel("Fonte 2").selectOption("source-2");
  await page.getByRole("button", { name: "Iniciar reprodução sem rótulos" }).click();
  await expect(page.getByLabel("Opção 1", { exact: true })).toBeVisible();
  await page.getByRole("radio", { name: "Preferida" }).first().check();
  await page.getByLabel("Comparei sem saber qual era a montagem dirigida ou o controle").check();
  await page.getByLabel("Vi os três vídeos completos em velocidade normal").check();
  await page.getByLabel("Conferi a leitura em tamanho de celular").check();
  await page.getByLabel("Conferi que o controle é uma concatenação direta da EDL").check();
  await page.getByLabel("Confirmei os mesmos materiais nos três vídeos").check();
  await page.getByLabel("Por que escolheu esta opção?").fill("O corte acompanha melhor a ação.");
  await page.getByRole("button", { name: "Registrar comparação" }).click();
  await expect.poll(() => submitted?.controlChecksum).toBe(checksum("c"));
  expect(submitted.controlEdl).toHaveLength(2);
  expect(submitted.editAChecksum).toBe(checksum("a"));
  expect(submitted.editBChecksum).toBe(checksum("b"));
  expect(submitted.blindReviewCompleted).toBe(true);
  expect(["edit_a", "edit_b", "concat_control"]).toContain(submitted.preferred);
  // Replacing the document while playback is open must discard its review session.
  await page.evaluate(record => (window as any).__contextualHarness.update(record), { ...doc, revision: 3 });
  await expect(page.getByText("Comparação cega: aguardando duas montagens desta fase no mesmo projeto.")).toBeVisible();
  await expect(page.getByLabel("Opção 1", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Registrar comparação" })).toHaveCount(0);
});

test("visual direction exposes missing voice without claiming a completed video", async ({ page }) => {
  const doc = { documentId: "production-empty", workspaceId: "workspace", revision: 1, version: 1,
    brief: { objective: "Explicar distribuição" }, assets: [],
    composition: { pages: [{ id: "page", width: 960, height: 540 }], narrative: {} } };
  await page.route("**/api/v1/studios/v1/editing/ai", r => r.fulfill({ json: { operations: [], label: "Gemini" } }));
  await page.route("**/api/v1/studios/v1/transcripts?*", r => r.fulfill({ json: [] }));
  await page.route("**/api/v1/studios/v1/editing/repertoire?*", r => r.fulfill({ json: { techniques: [] } }));
  await page.route("**/editing-plans/latest", r => r.fulfill({ json: null }));
  await page.route("**/production-runs", r => r.fulfill({ json: {
    id: "run", status: "blocked", stage: "composition", blockers: ["production_qualified_narration_required"],
    artifacts: { direction: { selectionReason: "A conexão mostra o caminho da ideia.", beats: [
      { id: "idea", initialState: "Ideia isolada", action: "Conectar pessoas", consequence: "Chegar ao público" },
    ] } },
  } }));
  await page.goto("/");
  await page.evaluate(async record => {
    const path = "/tests/fixtures/contextual-editing-harness.tsx";
    const { mountContextualHarness } = await import(path);
    (window as any).__contextualHarness = mountContextualHarness(record);
  }, doc);
  await page.getByLabel("Roteiro e informações de origem").fill("Uma ideia precisa encontrar pessoas.");
  await page.getByRole("button", { name: "Desenvolver montagem mista" }).click();
  await expect(page.getByText("Falta narração utilizável.", { exact: false })).toBeVisible();
  await page.getByText("Conceito e cenas").click();
  await expect(page.getByText("Ideia isolada", { exact: false })).toBeVisible();
  expect(await page.evaluate(() => (window as any).__contextualHarness.renders.length)).toBe(0);
});

test("motion starts from a script without source clips and displays missing narration", async ({ page }) => {
  const doc = { documentId: "motion-empty", workspaceId: "workspace", revision: 1, version: 1,
    brief: { objective: "Explicar distribuição" }, assets: [],
    composition: { pages: [{ id: "page", width: 960, height: 540 }], narrative: {} } };
  const plan = { id: "motion-plan", revision: 1, documentRevision: 1, status: "awaiting_choice",
    schemaVersion: "studio.contextual-edit-plan.v2", estimatedCostCents: 0, operations: [], materialRequests: [],
    direction: { scenes: [{ id: "opening", purpose: "Conectar a ideia às pessoas", durationFrames: 240 }] },
    blockers: [{ id: "voice", message: "Adicione a narração para esta cena.", alternatives: [] }] };
  let submitted: any;
  await page.route("**/api/v1/studios/v1/editing/ai", r => r.fulfill({ json: {
    operations: ["plan"], label: "Gemini", contextualV2: { configured: true } } }));
  await page.route("**/api/v1/studios/v1/transcripts?*", r => r.fulfill({ json: [] }));
  await page.route("**/api/v1/studios/v1/editing/repertoire?*", r => r.fulfill({ json: { techniques: [] } }));
  await page.route("**/editing-plans/latest", r => r.fulfill({ json: null }));
  await page.route("**/editing-ai-jobs", r => {
    submitted = r.request().postDataJSON();
    return r.fulfill({ json: { id: "plan-job", status: "succeeded", result: { plan } } });
  });
  await page.goto("/");
  await page.evaluate(async record => {
    const path = "/tests/fixtures/contextual-editing-harness.tsx";
    const { mountContextualHarness } = await import(path);
    (window as any).__contextualHarness = mountContextualHarness(record);
  }, doc);
  await page.getByLabel("Criar cenas com edição e motion").check();
  await page.getByLabel("Roteiro e informações de origem").fill("Uma ideia precisa encontrar pessoas.");
  await page.getByRole("button", { name: "Criar vídeo com esta direção" }).click();
  await expect.poll(() => submitted?.planVersion).toBe(2);
  expect(submitted.direction.beats).toEqual([]);
  await expect(page.getByText("Adicione a narração para esta cena.")).toBeVisible();
  await expect(page.getByText("Conectar a ideia às pessoas", { exact: false })).toBeVisible();
  expect(await page.evaluate(() => (window as any).__contextualHarness.renders.length)).toBe(0);
});

test("material choice and rejected copy remain visible before replanning", async ({ page }) => {
  const doc = { documentId: "needs-ui", workspaceId: "workspace", revision: 1, version: 1,
    brief: { objective: "Identificar a origem" }, assets: [],
    composition: { pages: [{ id: "page", width: 320, height: 320 }], mediaTimeline: {
      durationFrames: 50, frameRate: { numerator: 25, denominator: 1 },
      tracks: [{ id: "main", kind: "video", clips: [{ id: "source", enabled: true, assetId: "asset" }] }],
    } } };
  const plan = { id: "needs-plan", revision: 1, documentRevision: 1, status: "awaiting_choice", estimatedCostCents: 1,
    operations: [], blockers: [], editorialEvidence: [{ type: "editorial_admission", clipId: "source",
      message: "Texto sem fonte", proposedText: "Uma promessa sem comprovação" }],
    materialRequests: [{ id: "logo", clipId: "source", kind: "logo", query: "Marca de exemplo", purpose: "Identificar a origem",
      role: "support", officialRequired: true, exact: true, required: true, acceptanceCriteria: ["Preservar cores"],
      status: "awaiting_choice", candidates: [{ id: "selected-logo", title: "Arquivo oficial" }], sources: [], generationAllowed: false }],
  };
  let submitted: any;
  await page.route("**/api/v1/studios/v1/editing/ai", route => route.fulfill({ json: { operations: [], label: "" } }));
  await page.route("**/api/v1/studios/v1/transcripts?*", route => route.fulfill({ json: [] }));
  await page.route("**/api/v1/studios/v1/editing/repertoire?*", route => route.fulfill({ json: { techniques: [] } }));
  await page.route("**/api/v1/studios/v1/documents/needs-ui/editing-plans**", route => {
    if (!route.request().url().endsWith("/latest")) submitted = route.request().postDataJSON();
    return route.fulfill({ json: plan });
  });
  await page.goto("/");
  await page.evaluate(async record => {
    const path = "/tests/fixtures/contextual-editing-harness.tsx";
    const { mountContextualHarness } = await import(path);
    (window as any).__contextualHarness = mountContextualHarness(record);
  }, doc);
  await expect(page.getByText("Uma promessa sem comprovação", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Usar Arquivo oficial" }).click();
  await page.getByRole("button", { name: "Criar vídeo com esta direção" }).click();
  await expect.poll(() => submitted?.materialNeeds?.[0]?.assetId).toBe("selected-logo");
  expect(submitted.materialNeeds[0].officialRequired).toBe(true);
  expect(submitted.materialNeeds[0].candidates).toBeUndefined();
  expect(await page.evaluate(() => (window as any).__contextualHarness.renders.length)).toBe(0);
});

test("contextual editing waits for a choice and then generates the draft", async ({ page }) => {
  test.setTimeout(60_000);
  const bundled = process.env.CONTEXTUAL_COMPONENT_TEST === "1";
  const doc = { documentId: "contextual-ui", workspaceId: "workspace", revision: 1, version: 1,
    brief: { objective: "Mostrar a montagem do produto" }, assets: [],
    composition: { pages: [{ id: "page", width: 320, height: 320 }],
      mediaTimeline: { durationFrames: 50, frameRate: { numerator: 25, denominator: 1 },
        tracks: [{ id: "main", kind: "video", clips: [{ id: "source", label: "Demonstração", enabled: true, assetId: "asset" }] }] } } };
  const plan = { id: "plan-ui", revision: 1, documentRevision: 1, status: "awaiting_choice", estimatedCostCents: 2,
    operations: [{ operationId: "keep-source", beatId: "source", rationale: "Preservar a ressalva do roteiro.", expectedResult: "Fala completa." }],
    blockers: [{ id: "missing-support", message: "O apoio visual solicitado ainda não está disponível.", alternatives: [
      { id: "omit", label: "Continuar sem este recurso", impact: "A fala permanece intacta.", action: "omit_optional" },
      { id: "wait", label: "Aguardar e ajustar os materiais", impact: "A renderização permanece parada.", action: "wait" },
    ] }] };
  let applyCount = 0;
  let choiceCount = 0;
  let releaseLatest!: () => void;
  const latestReleased = new Promise<void>(resolve => { releaseLatest = resolve; });
  await page.route("**/api/v1/studios/v1/transcripts?*", route => route.fulfill({ json: [{
    id: "transcript-ui", assetId: "asset", revision: 3, status: "reviewed", segments: [{ text: "Não garante resultado." }],
  }] }));
  await page.route("**/api/v1/studios/v1/editing/repertoire?*", route => route.fulfill({ json: { techniques: [] } }));
  await page.route("**/api/v1/studios/v1/documents/contextual-ui/editing-plans**", async route => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/latest")) {
      await latestReleased;
      return route.fulfill({ json: null });
    }
    if (path.endsWith("/choices")) {
      choiceCount++;
      expect(route.request().postDataJSON().alternativeId).toBe("omit");
      return route.fulfill({ json: { ...plan, revision: 2, status: "ready", blockers: [] } });
    }
    if (path.endsWith("/apply")) {
      applyCount++;
      expect(choiceCount).toBe(1);
      return route.fulfill({ json: { ...doc, revision: 2 } });
    }
    expect(route.request().postDataJSON().intent.preserveMessage).toBe(true);
    const beat = route.request().postDataJSON().beats[0];
    expect(beat.transcriptId).toBe("transcript-ui");
    expect(beat.transcriptRevision).toBe(3);
    expect(beat.captionFromTranscript).toBe(true);
    expect(beat.sourceDecisions[0]).toMatchObject({ operation: "keep", status: "suggested", startMicroseconds: 200000, endMicroseconds: 1800000 });
    return route.fulfill({ json: plan });
  });
  await page.route("**/__contextual-test-host", route => route.fulfill({ contentType: "text/html", body: `
    <!doctype html><html><head>${bundled ? '<link rel="stylesheet" href="/contextual.css">' : ''}<script type="module">
    ${bundled ? '' : `
    import RefreshRuntime from '/@react-refresh';
    RefreshRuntime.injectIntoGlobalHook(window);
    window.$RefreshReg$ = () => {};
    window.$RefreshSig$ = () => type => type;
    `}
    window.__vite_plugin_react_preamble_installed__ = true;
    </script></head><body></body></html>` }));
  await page.goto("/__contextual-test-host");
  await page.waitForFunction(() => (window as any).__vite_plugin_react_preamble_installed__ === true);
  await page.evaluate(async record => {
    const path = "/tests/fixtures/contextual-editing-harness.tsx";
    const { mountContextualHarness } = await import(path);
    (window as any).__contextualHarness = mountContextualHarness(record);
  }, doc);
  const panel = page.getByRole("region", { name: "Edição contextual" });
  await panel.getByText("Direção por cena", { exact: true }).click();
  await panel.getByLabel("Transcrição da cena").selectOption("transcript-ui");
  await panel.getByLabel("Legendar a fala").check();
  await panel.getByLabel("Início na origem (segundos)").fill("0.2");
  await panel.getByLabel("Fim na origem (segundos)").fill("1.8");
  await panel.getByRole("button", { name: "Criar vídeo com esta direção" }).click();
  await expect(panel.getByText("O apoio visual solicitado ainda não está disponível.")).toBeVisible();
  const latestResponse = page.waitForResponse(response => response.url().endsWith("/editing-plans/latest"));
  releaseLatest();
  await latestResponse;
  await expect(panel.getByText("O apoio visual solicitado ainda não está disponível.")).toBeVisible();
  expect(applyCount).toBe(0);
  expect(await page.evaluate(() => (window as any).__contextualHarness.renders.length)).toBe(0);
  await panel.getByRole("button", { name: "Continuar sem este recurso" }).click();
  await expect.poll(() => applyCount).toBe(1);
  await expect.poll(() => page.evaluate(() => (window as any).__contextualHarness.renders.length)).toBe(1);
  await panel.getByText("Decisões de edição e ajustes").click();
  await expect(panel.getByText("Preservar a ressalva do roteiro.")).toBeVisible();
});

test("verified transformation applies only to its selected scene without a fictional human review", async ({ page }) => {
  const doc = { documentId: "resource-ui", workspaceId: "workspace", revision: 1, version: 1,
    brief: { objective: "Mostrar o produto" }, assets: [{ id: "original", mediaType: "video/mp4", rightsStatus: "verified" }],
    composition: { pages: [{ id: "page", width: 320, height: 320 }], mediaTimeline: {
      durationFrames: 150, frameRate: { numerator: 25, denominator: 1 }, tracks: [{ id: "main", kind: "video", clips: [
        { id: "scene", assetId: "original", enabled: true, label: "Cena do produto",
          timeline: { startFrame: 0, durationFrames: 150 }, source: { startMicroseconds: 0, durationMicroseconds: 6000000 } },
      ] }],
    } } };
  let applied = false;
  let reviews = 0;
  await page.route("**/api/v1/studios/v1/**", async route => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/editing/ai")) return route.fulfill({ json: {
      configured: true, operations: ["plan", "edit_video"], label: "Gemini" } });
    if (path.endsWith("/editing/repertoire")) return route.fulfill({ json: { techniques: [] } });
    if (path.endsWith("/editing/resources")) return route.fulfill({ json: [] });
    if (path.endsWith("/review")) { reviews++; return route.fulfill({ json: {} }); }
    if (path.endsWith("/editing-resources/apply")) {
      expect(route.request().postDataJSON()).toMatchObject({ expectedDocumentRevision: 1, assetId: "generated", targetClipId: "scene" });
      applied = true;
      return route.fulfill({ json: { ...doc, revision: 2 } });
    }
    if (path.endsWith("/editing-ai-jobs")) {
      expect(route.request().postDataJSON()).toMatchObject({ operation: "edit_video", sourceAssetId: "original",
        sourceStartSeconds: 1, durationSeconds: 3 });
      return route.fulfill({ json: { id: "generation", status: "succeeded",
        result: { assetId: "generated", checksumSha256: "a".repeat(64), status: "draft_material_ready" } } });
    }
    if (path.endsWith("/latest")) return route.fulfill({ json: null });
    return route.fulfill({ json: [] });
  });
  await page.route("**/__resource-test-host", route => route.fulfill({ contentType: "text/html",
    body: '<!doctype html><html><head><link rel="stylesheet" href="/contextual.css"></head><body></body></html>' }));
  await page.goto("/__resource-test-host");
  await page.evaluate(async record => {
    const path = "/tests/fixtures/contextual-editing-harness.tsx";
    const { mountContextualHarness } = await import(path);
    mountContextualHarness(record);
  }, doc);
  await page.getByText("Acervo e criação de materiais", { exact: true }).click();
  await page.getByRole("combobox", { name: "Operação", exact: true }).selectOption("edit_video");
  await page.getByLabel("Cena a transformar").selectOption("scene");
  await page.getByLabel("Início no vídeo de origem (segundos)").fill("1");
  await page.getByLabel("Duração do trecho (3 a 10 segundos)").fill("3");
  await page.getByLabel("Descreva a alteração").fill("Alterar somente a cor da camiseta");
  await page.getByRole("button", { name: "Gerar material", exact: true }).click();
  await page.getByRole("button", { name: "Aplicar transformação à cena", exact: true }).click();
  await expect.poll(() => applied).toBe(true);
  await expect(page.getByText("Trecho transformado aplicado à cena selecionada.")).toBeVisible();
  expect(reviews).toBe(0);
});
