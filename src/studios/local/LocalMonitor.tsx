import React from 'react';
import { apiFetchBlob } from '../../api';
import type { LocalDocument } from './localApi';
import { valueAt, containsPoint, canvasDocumentPoint } from './localModel';
export function LocalMonitor({ doc, frame, selected, onSelect }: {
    doc: LocalDocument;
    frame: number;
    selected?: string;
    onSelect: (id: string) => void;
}) {
    const canvas = React.useRef<HTMLCanvasElement>(null);
    const [images, setImages] = React.useState<Record<string, HTMLImageElement>>({});
    const [imageError, setImageError] = React.useState('');
    const page = doc.composition.pages[0];
    const assetIds = [...new Set(page.layers.map(layer => layer.properties.assetId).filter(Boolean))] as string[];
    const assetKey = JSON.stringify(assetIds);
    React.useEffect(() => {
        const controller = new AbortController();
        const urls: string[] = [];
        setImageError('');
        void Promise.all(assetIds.map(async (id) => {
            const url = URL.createObjectURL(await apiFetchBlob(`/api/v1/assets/${encodeURIComponent(id)}/content`, controller.signal));
            urls.push(url);
            const image = new Image();
            image.src = url;
            await image.decode();
            return [id, image] as const;
        })).then(entries => { if (!controller.signal.aborted)
            setImages(Object.fromEntries(entries)); })
            .catch(() => { if (!controller.signal.aborted)
            setImageError('Não foi possível carregar uma das imagens da prévia.'); });
        return () => { controller.abort(); urls.forEach(URL.revokeObjectURL); };
    }, [assetKey]);
    React.useEffect(() => {
        const element = canvas.current;
        if (!element)
            return;
        // Logical pixel dimensions preserve exported proportions; Retina gets native resolution.
        element.width = page.width;
        element.height = page.height;
        const context = element.getContext('2d');
        if (!context)
            return;
        const ctx = context;
        ctx.clearRect(0, 0, page.width, page.height);
        ctx.fillStyle = page.background;
        ctx.fillRect(0, 0, page.width, page.height);
        const total = doc.composition.mediaTimeline?.durationFrames || 1;
        for (const layer of [...page.layers].sort((a, b) => a.zIndex - b.zIndex)) {
            const style = layer.properties;
            const t = frame - (style.startFrame || 0);
            if (!layer.visible || t < 0 || t >= (style.durationFrames || total))
                continue;
            const x = layer.x + valueAt(style.keyframes, 'x', 0, t), y = layer.y + valueAt(style.keyframes, 'y', 0, t);
            const scale = valueAt(style.keyframes, 'scale', 1, t);
            ctx.save();
            ctx.translate(x + layer.width / 2, y + layer.height / 2);
            ctx.rotate(valueAt(style.keyframes, 'rotation', layer.rotation, t) * Math.PI / 180);
            ctx.scale(scale, scale);
            ctx.globalAlpha = valueAt(style.keyframes, 'opacity', layer.opacity, t);
            ctx.translate(-layer.width / 2, -layer.height / 2);
            if (style.shadow) {
                ctx.shadowColor = '#00000038';
                ctx.shadowBlur = 4;
            }
            if (layer.kind === 'shape') {
                ctx.fillStyle = style.fill || '#FF7F50';
                if (style.gradientEnd) {
                    const gradient = ctx.createLinearGradient(0, 0, 0, layer.height);
                    gradient.addColorStop(0, style.fill || '#FF7F50');
                    gradient.addColorStop(1, style.gradientEnd);
                    ctx.fillStyle = gradient;
                }
                ctx.beginPath();
                if (style.shape === 'ellipse')
                    ctx.ellipse(layer.width / 2, layer.height / 2, layer.width / 2, layer.height / 2, 0, 0, 2 * Math.PI);
                else
                    ctx.roundRect(0, 0, layer.width, layer.height, Math.min(style.radius || 0, layer.width / 2, layer.height / 2));
                ctx.fill();
            }
            else if (layer.kind === 'image' && style.assetId && images[style.assetId]) {
                const image = images[style.assetId];
                const crop = style.crop || { x: 0, y: 0, width: 1, height: 1 };
                let sw = image.width * crop.width, sh = image.height * crop.height, sx = image.width * crop.x, sy = image.height * crop.y;
                const ratio = Math.max(layer.width / sw, layer.height / sh);
                const w = layer.width / ratio, h = layer.height / ratio;
                sx += (sw - w) / 2;
                sy += (sh - h) / 2;
                sw = w;
                sh = h;
                ctx.filter = `brightness(${style.brightness ?? 1}) contrast(${style.contrast ?? 1}) saturate(${style.saturation ?? 1})`;
                ctx.drawImage(image, sx, sy, sw, sh, 0, 0, layer.width, layer.height);
            }
            else if (layer.kind === 'text') {
                const size = style.fontSize || 48;
                ctx.font = `${style.fontWeight || 700} ${size}px ${style.fontFamily === 'Liberation Sans' ? 'Arial' : '"Segoe UI", system-ui, sans-serif'}`;
                ctx.fillStyle = style.color || '#FFFFFF';
                ctx.textBaseline = 'top';
                ctx.textAlign = style.align || 'left';
                const lines: string[] = [];
                for (const paragraph of (style.text || '').split('\n')) {
                    let line = '';
                    for (const word of paragraph.split(/\s+/)) {
                        const next = (line + ' ' + word).trim();
                        if (ctx.measureText(next).width > layer.width && line) {
                            lines.push(line);
                            line = word;
                        }
                        else
                            line = next;
                    }
                    lines.push(line);
                }
                let wordIndex = 0;
                lines.forEach((line, row) => {
                    const width = ctx.measureText(line).width;
                    const left = style.align === 'center' ? (layer.width - width) / 2 : style.align === 'right' ? layer.width - width : 0;
                    let prefix = '';
                    ctx.textAlign = 'left';
                    for (const word of line.split(/\s+/).filter(Boolean)) {
                        if (style.textReveal !== 'words' || t >= wordIndex * (style.wordStaggerFrames || 6))
                            ctx.fillText(word, left + ctx.measureText(prefix).width, row * size * 1.3);
                        prefix += word + ' ';
                        wordIndex++;
                    }
                });
            }
            ctx.restore();
        }
    }, [doc.composition, frame, images]);
    const visibleLayers = page.layers.filter(layer => layer.visible && frame >= (layer.properties.startFrame || 0) && frame < (layer.properties.startFrame || 0) + (layer.properties.durationFrames || doc.composition.mediaTimeline?.durationFrames || 1));
    function choose(event: React.MouseEvent<HTMLCanvasElement>) {
        const box = event.currentTarget.getBoundingClientRect();
        const point = canvasDocumentPoint(event.clientX - box.left, event.clientY - box.top, box.width, box.height, page.width, page.height);
        if (!point) return;
        const { x, y } = point;
        const layer = [...visibleLayers].sort((a, b) => b.zIndex - a.zIndex).find(layer => {
            return containsPoint(layer, frame, x, y);
        });
        if (layer)
            onSelect(layer.id);
    }
    return <div className="lp-monitor"><canvas ref={canvas} tabIndex={0} onClick={choose} aria-label="Prévia de edição do projeto"/>{imageError && <p role="alert">{imageError}</p>}<p>{selected ? `Elemento: ${page.layers.find(layer => layer.id === selected)?.name || ''}` : 'Selecione um elemento na prévia ou em Camadas.'}</p></div>;
}
