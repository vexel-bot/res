import project from './project?project';
import {Renderer, RendererResult, Vector2} from '@motion-canvas/core';

declare global {
  interface Window {
    __resRender?: (settings: {width: number; height: number; fps: number; duration: number}) => Promise<number>;
  }
}

window.__resRender = async ({width, height, fps, duration}) => {
  const renderer = new Renderer(project);
  let result = RendererResult.Error;
  renderer.onFinished.subscribe(value => { result = value; });
  await renderer.render({
    name: 'res-motion-canvas', range: [0, duration], fps,
    exporter: {name: 'res/png-frames', options: {}},
    size: new Vector2(width, height), resolutionScale: 1,
    colorSpace: 'srgb', background: window.__resManifest?.background ?? '#101827',
  });
  return result;
};
