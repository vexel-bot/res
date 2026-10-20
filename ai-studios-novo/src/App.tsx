/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { ParticleSphereCanvas } from './components/ParticleSphereCanvas';

export default function App() {
  return (
    <main className="fixed inset-0 w-screen h-screen overflow-hidden bg-black select-none">
      <ParticleSphereCanvas />
    </main>
  );
}
