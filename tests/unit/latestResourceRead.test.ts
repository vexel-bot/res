import assert from "node:assert/strict";
import test from "node:test";
import { createLatestResourceRead } from "../../src/studios/latestResourceRead";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

test("last query wins even when old transport ignores abort and resolves later", async () => {
  const reader = createLatestResourceRead<string[]>(), first = deferred<string[]>(), second = deferred<string[]>();
  const commits: string[][] = [], errors: unknown[] = [];
  let firstSignal!: AbortSignal;
  const options = (read: (signal: AbortSignal) => Promise<string[]>) => ({
    isCurrent: () => true, read, onStart: () => {}, onValue: (v: string[]) => commits.push(v),
    onError: (e: unknown) => errors.push(e),
  });
  const old = reader.load(options(signal => { firstSignal = signal; return first.promise; }));
  const latest = reader.load(options(() => second.promise));
  assert.ok(firstSignal.aborted);
  second.resolve(["current match"]); await latest;
  first.resolve(["old query match"]); await old;
  assert.deepEqual(commits, [["current match"]]); assert.deepEqual(errors, []);
});

test("an old query failure cannot overwrite current successful results", async () => {
  const reader = createLatestResourceRead<string>(), oldResult = deferred<string>();
  const events: string[] = [];
  const options = (read: () => Promise<string>) => ({ isCurrent: () => true, read,
    onStart: () => {}, onValue: (v: string) => events.push(v), onError: () => events.push("error") });
  const old = reader.load(options(() => oldResult.promise));
  await reader.load(options(async () => "latest results"));
  oldResult.reject(new Error("old 503")); await old;
  assert.deepEqual(events, ["latest results"]);
});

test("obsolete document callback starts no request and does not abort the current document", async () => {
  const reader = createLatestResourceRead<string>(), result = deferred<string>();
  let context = "new-document", activeSignal!: AbortSignal;
  const commits: string[] = [];
  const current = reader.load({ isCurrent: () => context === "new-document",
    read: signal => { activeSignal = signal; return result.promise; }, onStart: () => {},
    onValue: value => commits.push(value), onError: () => assert.fail("unexpected failure") });
  await reader.load({ isCurrent: () => context === "old-document", read: () => { throw new Error("must not fetch"); },
    onStart: () => assert.fail("must not announce loading"), onValue: () => assert.fail("must not publish"),
    onError: () => assert.fail("must not publish failure") });
  assert.ok(!activeSignal.aborted); result.resolve("new document data"); await current;
  assert.deepEqual(commits, ["new document data"]);
  context = "another-document";
});

test("context switch discards an unabortable success before a replacement request starts", async () => {
  const reader = createLatestResourceRead<string>(), result = deferred<string>();
  let current = true;
  const pending = reader.load({ isCurrent: () => current, read: () => result.promise, onStart: () => {},
    onValue: () => assert.fail("old scope cannot publish"), onError: () => assert.fail("old scope cannot fail") });
  current = false; result.resolve("old workspace data"); await pending;
});

test("old completion cannot release a newer abort controller", async () => {
  const reader = createLatestResourceRead<string>(), first = deferred<string>(), second = deferred<string>();
  let latestSignal!: AbortSignal;
  const options = (read: (s: AbortSignal) => Promise<string>) => ({ isCurrent: () => true, read,
    onStart: () => {}, onValue: () => assert.fail("cancelled data cannot publish"), onError: () => assert.fail("cancelled error") });
  const old = reader.load(options(() => first.promise));
  const latest = reader.load(options(s => { latestSignal = s; return second.promise; }));
  first.resolve("old"); await old;
  reader.cancel(); assert.ok(latestSignal.aborted);
  second.resolve("new"); await latest;
});

test("cleanup can be followed by a fresh load on the same reader", async () => {
  const reader = createLatestResourceRead<string>(), pendingResult = deferred<string>();
  const values: string[] = [];
  const options = (read: () => Promise<string>) => ({ isCurrent: () => true, read,
    onStart: () => {}, onValue: (v: string) => values.push(v), onError: () => assert.fail("cancelled failure") });
  const old = reader.load(options(() => pendingResult.promise)); reader.cancel();
  await reader.load(options(async () => "fresh setup"));
  pendingResult.reject(new Error("aborted old setup")); await old;
  assert.deepEqual(values, ["fresh setup"]);
});

test("current failure is reported and a new read retrieves fresh inventory", async () => {
  const reader = createLatestResourceRead<string[]>();
  const errors: unknown[] = [], values: string[][] = [];
  const options = (read: () => Promise<string[]>) => ({ isCurrent: () => true, read,
    onStart: () => {}, onValue: (v: string[]) => values.push(v), onError: (e: unknown) => errors.push(e) });
  await reader.load(options(async () => { throw new Error("current 503"); }));
  await reader.load(options(async () => ["before import"]));
  await reader.load(options(async () => ["after import"]));
  assert.equal(errors.length, 1); assert.deepEqual(values, [["before import"], ["after import"]]);
});
