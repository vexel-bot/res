export function klicProviderConfig(env: NodeJS.ProcessEnv = process.env) {
  const model = env.KLIC_CHAT_MODEL?.trim() || 'gemini-2.5-flash';
  if (env.GOOGLE_GENAI_USE_VERTEXAI === 'true') {
    const project = env.GOOGLE_CLOUD_PROJECT?.trim();
    const location = env.GOOGLE_CLOUD_LOCATION?.trim() || 'global';
    const configured = Boolean(project && !project.startsWith('MY_'));
    return { mode: 'vertex' as const, model, project, location, configured, configurationIssue: configured ? undefined : 'KLIC_VERTEX_CONFIGURATION_REQUIRED' };
  }
  // GOOGLE_API_KEY may belong to YouTube/Radar and must never silently become
  // the KLIC credential. Pass GEMINI_API_KEY explicitly to the SDK.
  const apiKey = env.GEMINI_API_KEY?.trim();
  const configured = Boolean(apiKey && !apiKey.startsWith('MY_'));
  return { mode: 'developer-api' as const, model, apiKey, configured, configurationIssue: configured ? undefined : 'KLIC_GEMINI_API_KEY_REQUIRED', googleApiKeyIgnored: Boolean(env.GOOGLE_API_KEY?.trim()) };
}

export function klicTranscriptionModel(env: NodeJS.ProcessEnv = process.env) {
  return env.KLIC_TRANSCRIPTION_MODEL?.trim() || 'gemini-3.5-flash';
}
