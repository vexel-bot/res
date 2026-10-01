import {defineConfig} from 'vite';
import motionCanvasPackage from '@motion-canvas/vite-plugin';

// The published plugin is CommonJS with a nested default export under Vite's
// bundled config loader.
const motionCanvas = (motionCanvasPackage as unknown as {default: typeof motionCanvasPackage}).default ?? motionCanvasPackage;

export default defineConfig({
  plugins: [motionCanvas({project: './src/project.ts'})],
  server: {host: '127.0.0.1', strictPort: false},
});
