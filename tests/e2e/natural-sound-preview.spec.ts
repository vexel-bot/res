import { test, expect } from "@playwright/test";

test("Web Audio materializa offsets, sobreposição, ganho e fades após seek", async ({ page }) => {
  await page.goto("/login");
  const result = await page.evaluate(async () => {
    const path = "/src/studios/naturalSoundPreview.ts";
    const { scheduleNaturalSoundPreview } = await import(path);
    const sampleRate = 48_000;
    const render = async (seek: number) => {
      const context = new OfflineAudioContext(1, sampleRate * 3, sampleRate);
      const buffer = context.createBuffer(1, sampleRate * 2, sampleRate);
      buffer.getChannelData(0).fill(0.25);
      // Distinct source interval proves source offset, not just audible output.
      buffer.getChannelData(0).fill(0.5, 24_000);
      const plan = { duration: 3, assets: [], cues: [
        { id: "a", assetId: "s", start: 0.5, duration: 1.5, offset: 0.5, gain: 0.5, fadeIn: 0.3, fadeOut: 0.3 },
        { id: "b", assetId: "s", start: 1, duration: 0.5, offset: 0, gain: 0.25, fadeIn: 0, fadeOut: 0 },
      ] };
      scheduleNaturalSoundPreview(context, plan, new Map([["s", buffer]]), seek, 0);
      const pcm = (await context.startRendering()).getChannelData(0);
      return [0.1, 0.15, 0.4, 0.65, 0.9, 1.1, 1.85, 2.1].map((time) => pcm[Math.round(time * sampleRate)]);
    };
    return { full: await render(0), sought: await render(0.65) };
  });
  expect(result.full[0]).toBe(0);
  expect(result.full[2]).toBe(0);
  expect(result.full[3]).toBeCloseTo(0.125, 4);
  expect(result.full[4]).toBeCloseTo(0.25, 4);
  expect(result.full[5]).toBeCloseTo(0.3125, 4);
  expect(result.full[6]).toBeCloseTo(0.125, 4);
  expect(result.full[7]).toBe(0);
  expect(result.sought[0]).toBeCloseTo(0.25 * 5 / 6, 4);
  expect(result.sought[1]).toBeCloseTo(0.25, 4);
  expect(result.sought[2]).toBeCloseTo(0.3125, 4);
  expect(result.sought[5]).toBeCloseTo(0.25 * 5 / 6, 4);
  expect(result.sought[6]).toBe(0);
});

test("preview privado recusa checksum divergente e cancela carregamento sem tocar", async ({ page }) => {
  await page.goto("/login");
  await page.mouse.click(1, 1);
  const result = await page.evaluate(async () => {
    const path = "/src/studios/naturalSoundPreview.ts";
    const { NaturalSoundPreview } = await import(path);
    const plan = { duration: 1, cues: [{ id: "c", assetId: "s", start: 0, duration: 1, offset: 0, gain: 1, fadeIn: 0, fadeOut: 0 }],
      assets: [{ id: "s", checksum: "0".repeat(64), duration: 1 }] };
    const corrupt = new NaturalSoundPreview(async () => new Blob(["not the declared sound"]));
    let hashError = "";
    try { await corrupt.prepare(plan); } catch (error) { hashError = String(error); }
    corrupt.dispose();
    let capturedSignal: AbortSignal | undefined;
    let finish: ((blob: Blob) => void) | undefined;
    const pending = new NaturalSoundPreview(async (_id: string, signal: AbortSignal) => {
      capturedSignal = signal;
      return new Promise<Blob>((resolve) => { finish = resolve; });
    });
    const operation = pending.prepare(plan).then(() => "played", (error: Error) => error.name);
    pending.cancel();
    finish!(new Blob(["late response"]));
    const outcome = await operation;
    pending.dispose();
    return { hashError, cancelled: capturedSignal?.aborted, outcome };
  });
  expect(result.hashError).toContain("Checksum");
  expect(result.cancelled).toBe(true);
  expect(result.outcome).toBe("AbortError");
});

test("preview reaproveita decode só na sessão e recusa contexto de áudio suspenso", async ({ page }) => {
  await page.goto("/login");
  await page.mouse.click(1, 1);
  const result = await page.evaluate(async () => {
    const path = "/src/studios/naturalSoundPreview.ts";
    const { NaturalSoundPreview } = await import(path);
    const bytes = new ArrayBuffer(44 + 96_000);
    const view = new DataView(bytes);
    const word = (at: number, text: string) => [...text].forEach((letter, index) => view.setUint8(at + index, letter.charCodeAt(0)));
    word(0, "RIFF"); view.setUint32(4, bytes.byteLength - 8, true); word(8, "WAVE"); word(12, "fmt ");
    view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
    view.setUint32(24, 48_000, true); view.setUint32(28, 96_000, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true);
    word(36, "data"); view.setUint32(40, 96_000, true);
    for (let offset = 44; offset < bytes.byteLength; offset += 2) view.setInt16(offset, 8_000, true);
    const checksum = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), (value) => value.toString(16).padStart(2, "0")).join("");
    const plan = { duration: 1, cues: [{ id: "c", assetId: "s", start: 0, duration: 1, offset: 0, gain: 0.5, fadeIn: 0, fadeOut: 0 }],
      assets: [{ id: "s", checksum, duration: 1 }] };
    let downloads = 0;
    const load = async () => { downloads += 1; return new Blob([bytes], { type: "audio/wav" }); };
    const engine = new NaturalSoundPreview(load);
    await engine.prepare(plan);
    engine.sync(0.3); engine.stop();
    await engine.prepare(plan);
    const afterReplay = downloads;
    // Native AudioContext state transition, not a stubbed scheduler result.
    await engine.context.suspend();
    let interrupted = "";
    try { engine.sync(0.3); } catch (error) { interrupted = String(error); }
    engine.dispose();
    const anotherScope = new NaturalSoundPreview(load);
    await anotherScope.prepare(plan);
    anotherScope.dispose();
    return { afterReplay, downloads, interrupted };
  });
  expect(result.afterReplay).toBe(1);
  expect(result.downloads).toBe(2);
  expect(result.interrupted).toContain("interrompeu o áudio");
});
