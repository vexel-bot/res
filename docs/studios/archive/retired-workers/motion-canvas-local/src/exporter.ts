import {makePlugin, ObjectMetaField, type Exporter, type Project, type RendererSettings} from '@motion-canvas/core';

declare global {
  interface Window {
    __resPushFrame?: (frame: number, png: string) => Promise<void>;
  }
}

class ResPngExporter implements Exporter {
  static readonly id = 'res/png-frames';
  static readonly displayName = 'res PNG frames';
  static meta() { return new ObjectMetaField('res PNG frames', {}); }
  static async create(_project: Project, _settings: RendererSettings) { return new ResPngExporter(); }
  async handleFrame(canvas: HTMLCanvasElement, frame: number, _sceneFrame: number, _sceneName: string, signal: AbortSignal) {
    if (signal.aborted) return;
    if (frame >= (window as Window & {__resManifest?: {durationFrames: number}}).__resManifest!.durationFrames) return;
    if (!window.__resPushFrame) throw new Error('res_frame_sink_unavailable');
    await window.__resPushFrame(frame, canvas.toDataURL('image/png'));
  }
}

export default makePlugin({name: 'res/frames', exporters: () => [ResPngExporter]});
