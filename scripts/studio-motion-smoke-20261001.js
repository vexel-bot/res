// Run in an authenticated local Studio browser. Uses the real API, never mocks.
// Editorial intervention: this direction and original sound design are authored
// for the smoke test; this is not evidence of autonomous planning or Alight.
(async () => {
  const root = '/api/v1';
  const headers = {Authorization: `Bearer ${localStorage.getItem('nexus_access_token')}`};
  const api = async (path, method = 'GET', body, key) => {
    const response = await fetch(root + path, {method, headers: {...headers,
      ...(body instanceof FormData ? {} : {'Content-Type': 'application/json'}),
      ...(key ? {'Idempotency-Key': key} : {})},
      body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body)});
    const result = await response.json();
    if (!response.ok) throw new Error(`${method} ${path}: ${JSON.stringify(result.detail)}`);
    return result;
  };
  const bootstrap = await api('/bootstrap');
  const workspace = bootstrap.workspaces.find(w => w.name === 'Laboratório Motion 01-10');
  if (!workspace) throw new Error('isolated_study_workspace_required');
  const state = window.motionStudy = {workspaceId: workspace.id, status: 'preparing',
    interventions: ['Direction, type layout, timing and sound authored by Codex for this test.',
      'Uses registered Remotion components and existing FFmpeg finalization. No Alight execution.',
      'Original graphic study, not a commercial campaign or human-approved reference.'], apiSpendUsd: 0};
  const post = await api('/posts', 'POST', {workspaceId: workspace.id,
    title: 'Dê forma à ideia — estudo de motion 15 s', platform: 'instagram', format: 'reels',
    status: 'draft', origin: 'manual', objective: 'Testar tipografia, continuidade gráfica e som pelo Studio',
    copy: 'Estudo interno de composição. Avaliação visual humana pendente.', author: 'Laboratório de motion'});
  state.postId = post.id;

  // Original PCM sound: soft percussive attacks, filtered noise sweeps and a
  // two-note tonal punctuation, synchronized to the authored graphic events.
  const sr = 48000, seconds = 15, samples = sr * seconds;
  const buffer = new ArrayBuffer(44 + samples * 2), view = new DataView(buffer);
  const ascii = (offset, text) => [...text].forEach((c, i) => view.setUint8(offset + i, c.charCodeAt(0)));
  ascii(0, 'RIFF'); view.setUint32(4, 36 + samples * 2, true); ascii(8, 'WAVE');
  ascii(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
  view.setUint16(22, 1, true); view.setUint32(24, sr, true); view.setUint32(28, sr * 2, true);
  view.setUint16(32, 2, true); view.setUint16(34, 16, true); ascii(36, 'data');
  view.setUint32(40, samples * 2, true);
  const events = [0.2, 1.6, 3.7, 5.2, 5.5, 5.8, 7.1, 8.6, 9.5, 10.4, 11.5];
  let seed = 20261001, low = 0;
  for (let i = 0; i < samples; i++) {
    const t = i / sr;
    seed = (1664525 * seed + 1013904223) >>> 0;
    const noise = seed / 2147483648 - 1;
    low = low * .92 + noise * .08;
    let value = 0;
    events.forEach((at, index) => {
      const dt = t - at;
      if (dt >= 0 && dt < .48) value += .32 * Math.exp(-dt * 18) *
        Math.min(1, dt * 700) * Math.sin(2 * Math.PI * (90 + index * 13) * dt);
    });
    [3.4, 7.9, 10.9].forEach(at => {
      const dt = t - at;
      if (dt >= 0 && dt < .6) value += .3 * low * Math.sin(Math.PI * dt / .6) ** 2;
    });
    [11.65, 11.9].forEach((at, index) => {
      const dt = t - at;
      if (dt >= 0 && dt < 1.8) value += .10 * Math.sin(2 * Math.PI * (index ? 440 : 330) * dt)
        * Math.exp(-dt * 2.5) * Math.min(1, dt * 120);
    });
    view.setInt16(44 + i * 2, Math.max(-.85, Math.min(.85, value)) * 32767, true);
  }
  const checksum = [...new Uint8Array(await crypto.subtle.digest('SHA-256', buffer))]
    .map(x => x.toString(16).padStart(2, '0')).join('');
  const form = new FormData(); form.set('workspace_id', workspace.id);
  form.set('title', 'Motion study — desenho sonoro original'); form.set('tags', 'study,owned,original,sound-design');
  form.set('file', new Blob([buffer], {type: 'audio/wav'}), 'motion-study-original.wav');
  const sound = await api('/assets/upload', 'POST', form);
  const soundRef = {id: sound.id, mediaType: 'audio/wav', checksum, rightsStatus: 'unknown', origin: 'user-upload',
    provenance: {purpose: 'natural-sound-candidate', sourceDeclaration: 'PCM synthesized by the versioned smoke-test script',
      licenseDeclaration: 'Original sound authored for this internal res study; no third-party samples',
      audio: {durationSeconds: 15}, editingResource: {kind: 'sound_effect', action: 'Graphic event accents'}}};
  let document = await api('/studios/v1/documents', 'POST', {workspaceId: workspace.id, postId: post.id,
    title: post.title, contentType: 'video', brandRevision: 1,
    brief: {objective: post.objective, audience: 'Equipe interna do res', hook: 'Uma ideia ganha forma e ritmo',
      cta: 'Dê forma à ideia.', format: 'reels', tone: 'Editorial, preciso e expressivo',
      restrictions: ['Estudo interno; não publicar como campanha aprovada.', 'Sem locução ou materiais de terceiros.']},
    assets: [soundRef], composition: {pages: [{id: 'motion-page', width: 1080, height: 1920,
      safeArea: 90, background: '#111214', durationMs: 15000, layers: []}]}});
  state.documentId = document.documentId;
  const review = await api(`/studios/v1/documents/${document.documentId}/assets/${sound.id}/rights-reviews`, 'POST',
    {expectedDocumentRevision: document.revision, assetChecksumSha256: checksum, decision: 'verified', basis: 'owned',
      sourceReference: 'scripts/studio-motion-smoke-20261001.js (original PCM synthesis)',
      rightsReference: 'Original internal res study, no third-party samples', noExpirationConfirmed: true,
      notes: 'Authored for this test. Rights review does not assert aesthetic quality.'}, `motion-owned-${post.id}`);
  document = review.document;
  state.soundAssetId = sound.id;
  const k = (frame, value, easing = 'cubic_bezier') => ({frame, value, easing,
    ...(easing === 'cubic_bezier' ? {cubicBezier: [.22, .75, .25, 1]} : {})});
  const anim = (property, ...keyframes) => ({property, keyframes});
  const el = (id, kind, start, duration, x, y, width, height, extra = {}) =>
    ({id, kind, startFrame: start, durationFrames: duration, x, y, width, height,
      purpose: `Compor o estudo tipográfico: ${id}`, zIndex: 5, ...extra});
  const type = (id, text, start, duration, y, size, extra = {}) =>
    el(id, 'text', start, duration, 90, y, 900, size * 1.35,
      {text, fontSize: size, lineHeight: 1, fontWeight: 800, color: '#f1eedf', visualRole: 'text', ...extra});
  const elements = [
    type('signature', 'res / motion study', 0, 450, 155, 26, {fontWeight: 500, letterSpacing: 2, color: '#999b91'}),
    type('opening-small', 'TUDO COMEÇA COM', 0, 104, 660, 32, {letterSpacing: 4,
      animations: [anim('opacity', k(0, 0), k(10, 1), k(92, 1), k(103, 0))]}),
    type('idea', 'UMA IDEIA.', 6, 145, 748, 124, {visualRole: 'hero',
      animations: [anim('position_y', k(0, 64), k(20, 0), k(96, 0), k(135, -290), k(144, -310)),
        anim('scale_x', k(0, .96), k(20, 1), k(96, 1), k(144, .74)),
        anim('scale_y', k(0, .96), k(20, 1), k(96, 1), k(144, .74)),
        anim('opacity', k(0, 0), k(7, 1), k(130, 1), k(144, 0))]}),
    el('seed', 'shape', 0, 450, 470, 1060, 140, 140, {shape: 'ellipse', radius: 70, fill: '#d5f26c', visualRole: 'accent',
      animations: [anim('scale_x', k(0, .001), k(6, 1), k(45, 1), k(54, .8), k(74, 1), k(106, 1), k(140, .5),
        k(236, .5), k(255, 1), k(328, 1), k(350, .32), k(449, .32)),
        anim('scale_y', k(0, .001), k(6, 1), k(45, 1), k(54, 1.15), k(74, 1), k(106, 1), k(140, .5),
          k(236, .5), k(255, 1), k(328, 1), k(350, .32), k(449, .32)),
        anim('position_x', k(0, 0), k(106, 0), k(140, 355), k(236, 355), k(255, -330), k(328, -330), k(350, 380), k(449, 380)),
        anim('position_y', k(0, 0), k(106, 0), k(140, -480), k(236, -480), k(255, 430), k(328, 430), k(350, -810), k(449, -810))]}),
    type('gains', 'GANHA', 120, 120, 720, 155, {color: '#d5f26c',
      animations: [anim('position_x', k(0, -60), k(20, 0), k(100, 0), k(119, 40)),
        anim('opacity', k(0, 0), k(10, 1), k(104, 1), k(119, 0))]}),
    type('rhythm', 'RITMO.', 133, 107, 910, 162, {
      animations: [anim('position_x', k(0, 60), k(20, 0), k(87, 0), k(106, -40)),
        anim('opacity', k(0, 0), k(10, 1), k(91, 1), k(106, 0))]}),
    type('rhythm-sub', 'PULSO · PAUSA', 158, 84, 1160, 27, {letterSpacing: 2, color: '#999b91',
      animations: [anim('opacity', k(0, 0), k(10, 1), k(70, 1), k(83, 0))]}),
    el('drawn-line', 'path', 154, 86, 90, 1116, 900, 16, {color: '#d5f26c', strokeWidth: 6,
      points: [{x: 0,y: 10},{x: 140,y: 10},{x: 210,y: 0},{x: 310,y: 10},{x: 650,y: 10},{x: 900,y: 10}],
      reveal: 'path', revealFrames: 30, animations: [anim('opacity', k(0, 1), k(72, 1), k(85, 0))]}),
    type('each', 'CADA CORTE', 240, 99, 650, 91, {
      animations: [anim('position_y', k(0, 40), k(16, 0)), anim('opacity', k(0, 0), k(8, 1), k(88, 1), k(98, 0))]}),
    type('has', 'TEM', 258, 81, 835, 150, {color: '#d5f26c',
      animations: [anim('position_y', k(0, 35), k(12, 0)), anim('opacity', k(0, 0), k(7, 1), k(70, 1), k(80, 0))]}),
    type('reason', 'MOTIVO.', 285, 54, 1140, 145, {
      animations: [anim('position_y', k(0, 35), k(12, 0)), anim('opacity', k(0, 0), k(7, 1), k(43, 1), k(53, 0))]}),
    type('final-top', 'DÊ FORMA', 341, 109, 690, 147, {
      animations: [anim('position_y', k(0, 40), k(18, 0)), anim('opacity', k(0, 0), k(9, 1))]}),
    type('final-bottom', 'À IDEIA.', 351, 99, 885, 156, {color: '#d5f26c',
      animations: [anim('position_y', k(0, 40), k(18, 0)), anim('opacity', k(0, 0), k(9, 1))]}),
    type('final-sub', 'CRIE COM INTENÇÃO.', 369, 81, 1190, 30, {fontWeight: 500, letterSpacing: 3,
      animations: [anim('opacity', k(0, 0), k(12, 1))]}),
    type('study-label', 'ESTUDO INTERNO', 0, 450, 1695, 22,
      {fontWeight: 500, letterSpacing: 1.5, color: '#999b91'}),
  ];
  const direction = {schemaVersion: 'studio.contextual-plan-request.v2', expectedDocumentRevision: document.revision,
    executionScope: 'audiovisual', frameRate: {numerator: 30, denominator: 1},
    intent: {objective: post.objective, script: 'Tudo começa com uma ideia. Ganha ritmo. Cada corte tem motivo. Dê forma à ideia.',
      pacing: 'balanced', preserveMessage: true, reducedMotion: false}, scenes: [{id: 'kinetic-study',
      purpose: 'Uma forma persistente conduz a coreografia tipográfica até um encerramento de leitura.',
      durationFrames: 450, background: '#111214', elements,
      nativeComponents: [{component: 'integrated_typography', version: 1,
        targetIds: ['gains', 'rhythm', 'each', 'has', 'reason', 'final-top', 'final-bottom'], entranceFrames: 10, travelRatio: .06}],
      audio: [{id: 'sound-design', role: 'effect', purpose: 'Ataques e passagens sincronizados às entradas e ao motivo persistente.',
        assetId: sound.id, startFrame: 0, durationFrames: 450, gainDb: -4, fadeInFrames: 3, fadeOutFrames: 18}],
      verification: ['Ler a mensagem em tamanho de celular.', 'O motivo circular persiste entre as três frases.',
        'Ataques em 0.2, 1.6, 3.7, 5.2, 5.5, 5.8, 7.1, 8.6, 9.5, 10.4 e 11.5 s.',
        'Conclusão técnica não representa aprovação humana.']} ]};
  state.direction = direction;
  const plan = await api(`/studios/v1/documents/${document.documentId}/editing-plans`, 'POST', direction,
    `motion-plan-${post.id}`);
  state.plan = plan;
  state.status = plan.status;
  state.url = `/content/${post.id}/edit?mode=video`;
  return {workspaceId: workspace.id, postId: post.id, documentId: document.documentId,
    planId: plan.id, status: plan.status, blockers: plan.blockers, url: state.url};
})().catch(e => { if(window.motionStudy) window.motionStudy.error = e.message; return {error: e.message}; });
