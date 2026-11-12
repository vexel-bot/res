/** Local editorial recovery for the authorized deep production experiment. */
const fs = require('node:fs');
const path = require('node:path');
const { request, get, base, hash, sleep } = require('./clicko-motion-editorial-proof.cjs');

const output = path.resolve(process.argv[3]);
const paid = JSON.parse(fs.readFileSync(path.join(output, 'recibo.json'), 'utf8'));
const receiptFile = path.join(output, 'recibo-local.json');
const receipt = fs.existsSync(receiptFile) ? JSON.parse(fs.readFileSync(receiptFile)) : {};
const save = () => fs.writeFileSync(receiptFile, JSON.stringify(receipt, null, 2));
const key = 'clicko-open-deep-local-recovery-v3';
const fps = 24;
const ink = '#101822';
const paper = '#FFF5E9';
const accent = '#FFB573';
const frames = (seconds) => Math.round(seconds * fps);
const timing = (start, end) => ({ startFrame: frames(start), durationFrames: frames(end) - frames(start) });
const motion = (property, frame, value, easing = 'linear') => ({ property, frame, value, easing });
const enter = (delay = 0) => [motion('opacity', 0, 0), motion('opacity', delay + 6, 1, 'ease-out'),
    motion('y', 0, 18), motion('y', delay + 10, 0, 'ease-out')];

function layer(id, kind, box, zIndex, start, end, properties) {
    const [x, y, width, height] = box;
    return { id, name: id, kind, x, y, width, height, zIndex,
        properties: { schemaVersion: 'studio.local-layer.v1', ...timing(start, end), ...properties } };
}

function text(id, value, box, start, end, fontSize, color = paper, keyframes = []) {
    return layer(id, 'text', box, 10, start, end, { text: value, fontSize, color, keyframes });
}

function shape(id, box, start, end, fill, keyframes = [], radius = 0) {
    return layer(id, 'shape', box, 4, start, end, { shape: 'rectangle', fill, radius, keyframes });
}

function clip(id, assetId, start, end, offset, keyframes = []) {
    const timeline = timing(start, end);
    return { id, assetId, timeline, source: { startMicroseconds: Math.round(offset * 1e6),
        durationMicroseconds: Math.round(timeline.durationFrames / fps * 1e6) },
        transform: { originalAudioEnabled: false }, keyframes };
}

async function main() {
    await request('GET', '/api/governance/auth/session');
    const source = paid.document;
    const [detail, , , footage, score] = paid.assets;
    const layers = [
        shape('campo-titulo', [0, 696, 540, 264], 0, 4.5, ink),
        shape('linha-do-corte', [36, 696, 468, 5], 0, 4.5, accent,
            [motion('scale', 0, .1), motion('scale', 18, 1, 'ease-out')]),
        text('identidade-abertura', 'CLICKO / STUDIO DE VÍDEO', [36, 723, 460, 38], .15, 4.5, 21, accent, enter()),
        text('gancho-primeira-linha', 'O próximo corte', [36, 770, 468, 68], .4, 4.5, 48, paper, enter()),
        text('gancho-segunda-linha', 'muda a história.', [36, 835, 468, 68], .85, 4.5, 48, paper, enter()),
        shape('fundo-retorno', [0, 0, 540, 960], 11.25, 18, ink),
        shape('estado-antes', [36, 402, 468, 66], 11.25, 12.5, '#473426', [], 12),
        shape('estado-depois-a', [36, 402, 218, 66], 12.5, 15, '#A85B36',
            [motion('x', 0, 14), motion('x', 9, 0, 'ease-out')], 12),
        shape('estado-depois-b', [268, 402, 236, 66], 12.5, 15, accent,
            [motion('x', 0, -14), motion('x', 9, 0, 'ease-out')], 12),
        text('continuidade-um', 'Dê direção ao', [36, 530, 470, 67], 11.25, 15, 49, paper, enter()),
        text('continuidade-dois', 'que você gravou.', [36, 596, 470, 67], 11.65, 15, 49, paper, enter()),
        shape('fecho-acento', [36, 410, 66, 6], 15, 18, accent),
        text('marca-fecho', 'Clicko', [36, 431, 465, 104], 15, 18, 76),
        text('cta-fecho', 'Abra o Studio de Vídeo.', [36, 554, 465, 110], 15, 18, 39, accent),
    ];
    const composition = {
        pages: [{ id: 'main', width: 540, height: 960, durationMs: 18000, background: ink, layers }], tracks: [],
        narrative: { experiment: { provenance: 'local_editorial_recovery', originalTask: '37ede534-6076-4f49-b0cc-752833649e8b' } },
        mediaTimeline: { durationFrames: 432, frameRate: { numerator: 24, denominator: 1 }, tracks: [
            { id: 'visual', kind: 'video', muted: true, clips: [
                clip('registro-no-celular', footage.id, 0, 4.5, 1.15, [motion('scale', 0, 1), motion('scale', 107, 1.055)]),
                clip('prova-real-do-corte', detail.id, 4.5, 11.25, .166667),
            ] },
            { id: 'music', kind: 'audio', clips: [{ id: 'score', assetId: score.id, timeline: timing(0, 18), gainDb: 9 }] },
        ] },
    };
    if (!receipt.document) {
        receipt.document = await request('POST', base + '/documents', {
            workspaceId: source.workspaceId, contentType: 'video', brandRevision: 1,
            title: 'Clicko · o próximo corte · recuperação local', brief: source.brief,
            composition, assets: [detail, footage, score],
        }, { key: key + '-doc' });
        save();
    }
    if (!receipt.job || receipt.job.status === 'failed') {
        receipt.startedAt = Date.now();
        receipt.job = await request('POST', base + '/video/documents/' + receipt.document.documentId + '/render-jobs',
            { expectedRevision: receipt.document.revision }, { key: key + '-render' });
        save();
    }
    for (let i = 0; i < 150; i++) {
        const job = await get(base + '/jobs/' + receipt.job.id);
        if (['failed', 'cancelled'].includes(job.status)) throw Error(job.errorCode + ' ' + job.errorMessage);
        if (job.status === 'succeeded') {
            const result = job.result;
            const bytes = await request('GET', result.downloadUrl, null, { bytes: true });
            if (hash(bytes) !== result.checksumSha256 || result.externalCostUsd !== 0) throw Error('Invalid export receipt');
            fs.writeFileSync(path.join(output, 'video-clicko-recuperacao-local.mp4'), bytes);
            fs.writeFileSync(path.join(output, 'projeto-editavel-local.json'), JSON.stringify(receipt.document, null, 2));
            receipt.result = result;
            receipt.renderWallSeconds = (Date.now() - receipt.startedAt) / 1000;
            save();
            console.log(JSON.stringify({ documentId: receipt.document.documentId, jobId: job.id,
                renderWallSeconds: receipt.renderWallSeconds, durationSeconds: result.durationSeconds, externalCostUsd: 0 }));
            return;
        }
        await sleep(1000);
    }
    throw Error('Local render still pending');
}

main().catch(error => { console.error(error.message); process.exitCode = 1; });
