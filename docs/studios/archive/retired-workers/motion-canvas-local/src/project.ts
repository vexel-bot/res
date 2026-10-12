import {makeProject} from '@motion-canvas/core';
import scene from './scene?scene';
import exporter from './exporter';

export default makeProject({scenes: [scene], plugins: [exporter()]});
