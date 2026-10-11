import assert from "node:assert/strict";
import test from "node:test";
import { loadVideoStudioResources, videoStudioSupportResource } from "../../src/studios/videoStudioLoading";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
const settle = () => new Promise<void>(resolve => setImmediate(resolve));

test("project is ready before support starts and remains ready with slow or failed catalogues", async () => {
  const core = deferred<void>(), slow = deferred<string>();
  const events: string[] = [], failures: string[] = [];
  const current = () => true;
  const resource = (label: string, load: () => Promise<string>) => videoStudioSupportResource({
    label, load: () => { events.push(`start:${label}`); return load(); },
    commit: value => events.push(`${label}:${value ?? "unavailable"}`),
  }, current, message => failures.push(message));
  const loading = loadVideoStudioResources({
    loadProject: async () => { await core.promise; events.push("project:ready"); },
    support: [resource("slow", () => slow.promise), resource("fast", async () => "real-data"),
      resource("failed", async () => { throw new Error("503"); })],
    isCurrent: current, onSupportLoading: value => events.push(`support:loading:${value}`),
  });
  await settle(); assert.deepEqual(events, []);
  core.resolve(); await loading; await settle();
  assert.equal(events[0], "project:ready");
  assert.ok(events.includes("fast:real-data"));
  assert.ok(events.includes("failed:unavailable"));
  assert.deepEqual(failures, ["failed: 503"]);
  assert.ok(!events.includes("support:loading:false"));
  slow.resolve("late-data"); await settle();
  assert.ok(events.includes("slow:late-data"));
  assert.equal(events.at(-1), "support:loading:false");
});

test("a failed project load remains a critical error and does not launch support requests", async () => {
  let started = false;
  await assert.rejects(loadVideoStudioResources({
    loadProject: async () => { throw new Error("document forbidden"); },
    support: [async () => { started = true; }], isCurrent: () => true,
    onSupportLoading: () => { throw new Error("must not announce background loading"); },
  }), /document forbidden/);
  assert.equal(started, false);
});

test("responses from a superseded project cannot publish data, warnings or loading completion", async () => {
  const success = deferred<string>(), failure = deferred<string>();
  let current = true;
  const commits: unknown[] = [], warnings: string[] = [], loadingStates: boolean[] = [];
  const resource = (label: string, result: Promise<string>) => videoStudioSupportResource({
    label, load: () => result, commit: value => commits.push(value),
  }, () => current, message => warnings.push(message));
  await loadVideoStudioResources({ loadProject: async () => {},
    support: [resource("success", success.promise), resource("failure", failure.promise)],
    isCurrent: () => current, onSupportLoading: value => loadingStates.push(value),
  });
  await settle(); current = false;
  success.resolve("old-project-data"); failure.reject(new Error("old-project-error"));
  await settle();
  assert.deepEqual(commits, []); assert.deepEqual(warnings, []);
  assert.deepEqual(loadingStates, [true]);
});

test("an already superseded load does not start background requests", async () => {
  let started = false;
  await loadVideoStudioResources({ loadProject: async () => {},
    support: [async () => { started = true; }], isCurrent: () => false,
    onSupportLoading: () => { throw new Error("stale load must not update UI"); },
  });
  assert.equal(started, false);
});
