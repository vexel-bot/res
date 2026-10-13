import test from 'node:test';
import assert from 'node:assert/strict';
import { shouldFinishVoiceTurn, shouldInterruptKlicSpeech, shouldRestartVoiceCapture, transcriptDisposition } from './voiceConversation';

test('dictation creates a draft while continuous voice sends the transcript', () => {
  assert.equal(transcriptDisposition('dictation'), 'draft');
  assert.equal(transcriptDisposition('conversation'), 'send');
});

test('only an unmuted continuous session restarts listening after speech', () => {
  assert.equal(shouldRestartVoiceCapture('conversation', false), true);
  assert.equal(shouldRestartVoiceCapture('conversation', true), false);
  assert.equal(shouldRestartVoiceCapture('dictation', false), false);
  assert.equal(shouldRestartVoiceCapture(null, false), false);
});

test('voice turns use silence detection, no-speech timeout and a hard duration limit', () => {
  assert.equal(shouldFinishVoiceTurn({ elapsedMs: 14_999, silenceMs: 14_999, heardVoice: false }), false);
  assert.equal(shouldFinishVoiceTurn({ elapsedMs: 15_001, silenceMs: 15_001, heardVoice: false }), 'no-speech');
  assert.equal(shouldFinishVoiceTurn({ elapsedMs: 4_000, silenceMs: 1_399, heardVoice: true }), false);
  assert.equal(shouldFinishVoiceTurn({ elapsedMs: 4_000, silenceMs: 1_401, heardVoice: true }), 'complete');
  assert.equal(shouldFinishVoiceTurn({ elapsedMs: 60_001, silenceMs: 0, heardVoice: true }), 'complete');
});

test('barge-in requires sustained speech above the noise threshold', () => {
  assert.equal(shouldInterruptKlicSpeech(0.056, 241), true);
  assert.equal(shouldInterruptKlicSpeech(0.054, 500), false);
  assert.equal(shouldInterruptKlicSpeech(0.08, 239), false);
});
