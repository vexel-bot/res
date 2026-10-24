import 'dotenv/config';
import { createTokenCipher } from '../server/integrations/crypto';
import { socialProviderRegistry } from '../server/integrations/providers/registry';

const providerId = process.argv[2] || 'x';
const provider = socialProviderRegistry().get(providerId as never);

if (!provider) {
  console.error(JSON.stringify({ provider: providerId, error: 'unknown_provider' }));
  process.exitCode = 1;
} else {
  const credentials = provider.credentials();
  let cipher = false;
  try {
    cipher = Boolean(createTokenCipher(process.env.SOCIAL_TOKEN_ENCRYPTION_KEY));
  } catch {
    // The diagnostic intentionally reports only availability, never key material.
  }

  if (!credentials) {
    console.log(JSON.stringify({ provider: providerId, configured: false, cipher }));
  } else {
    const authorizationUrl = new URL(provider.authorizationUrl({
      credentials,
      redirectUri: credentials.redirectUri,
      state: 'diagnostic-state',
      codeChallenge: provider.usesPkce ? 'diagnostic-challenge' : undefined,
    }));

    console.log(JSON.stringify({
      provider: providerId,
      configured: true,
      cipher,
      host: authorizationUrl.host,
      path: authorizationUrl.pathname,
      scope: authorizationUrl.searchParams.get('scope'),
      redirectUri: authorizationUrl.searchParams.get('redirect_uri'),
      responseType: authorizationUrl.searchParams.get('response_type'),
      pkce: authorizationUrl.searchParams.get('code_challenge_method'),
    }));
  }
}
