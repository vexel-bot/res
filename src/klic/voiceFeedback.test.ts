import test from 'node:test';
import assert from 'node:assert/strict';
import { KlicVoiceFeedbackSession, type KlicVoiceCue } from './voiceFeedback';

test('KLIC cues play once per listening session, not between continuous voice turns', () => {
  const cues: KlicVoiceCue[] = [];
  const feedback = new KlicVoiceFeedbackSession(cue => { cues.push(cue); });
  feedback.listeningStarted();
  feedback.listeningStarted(); // A recognition restart inside the same conversation.
  feedback.listeningStarted(); // Listening again after transcription and TTS.
  assert.deepEqual(cues, ['start']);
  feedback.listeningEnded();
  feedback.listeningEnded();
  assert.deepEqual(cues, ['start', 'end']);
  feedback.listeningStarted(); // Explicitly resumed after the microphone was muted.
  feedback.listeningEnded();
  assert.deepEqual(cues, ['start', 'end', 'start', 'end']);
});

test('a delayed cue cannot play after the listening transition was superseded', () => {
  const pending: Array<{ cue: KlicVoiceCue; stillCurrent: () => boolean }> = [];
  const feedback = new KlicVoiceFeedbackSession((cue, stillCurrent) => { pending.push({ cue, stillCurrent }); });
  feedback.listeningEnded(); // Permission denied or cancelled before capture: no sound.
  assert.equal(pending.length, 0);
  feedback.listeningStarted();
  feedback.listeningEnded();
  assert.equal(pending[0].stillCurrent(), false);
  assert.equal(pending[1].stillCurrent(), true);
});
