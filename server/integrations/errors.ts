export class SocialIntegrationError extends Error {
  constructor(
    readonly code: string,
    readonly status: number,
    readonly publicMessage: string,
  ) {
    super(code);
    this.name = 'SocialIntegrationError';
  }
}

export function publicIntegrationError(error: unknown) {
  if (error instanceof SocialIntegrationError) return error;
  if (error instanceof DOMException && error.name === 'TimeoutError') {
    return new SocialIntegrationError('SOCIAL_PROVIDER_TIMEOUT', 504, 'A plataforma demorou para responder. Tente novamente.');
  }
  return new SocialIntegrationError('SOCIAL_PROVIDER_UNAVAILABLE', 502, 'Não foi possível concluir a comunicação com a plataforma.');
}

export function callbackReason(error: unknown) {
  const failure = publicIntegrationError(error);
  if (failure.code === 'SOCIAL_PERMISSION_INSUFFICIENT') return 'permission_insufficient';
  if (failure.code === 'SOCIAL_AUTHORIZATION_REVOKED') return 'authorization_revoked';
  if (failure.code === 'SOCIAL_CONFIGURATION_REQUIRED') return 'configuration_required';
  return 'provider_error';
}
