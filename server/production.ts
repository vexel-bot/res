import { randomUUID } from 'node:crypto';
import type { NextFunction, Request, Response } from 'express';
import { createTokenCipherFromEnvironment } from './integrations/crypto';

const providerVariables = [
  ['META', 'META_APP_ID', 'META_APP_SECRET', 'META_REDIRECT_URI'],
  ['GOOGLE', 'GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'GOOGLE_REDIRECT_URI'],
  ['TIKTOK', 'TIKTOK_CLIENT_KEY', 'TIKTOK_CLIENT_SECRET', 'TIKTOK_REDIRECT_URI'],
  ['LINKEDIN', 'LINKEDIN_CLIENT_ID', 'LINKEDIN_CLIENT_SECRET', 'LINKEDIN_REDIRECT_URI'],
  ['PINTEREST', 'PINTEREST_APP_ID', 'PINTEREST_APP_SECRET', 'PINTEREST_REDIRECT_URI'],
  ['THREADS', 'THREADS_APP_ID', 'THREADS_APP_SECRET', 'THREADS_REDIRECT_URI'],
  ['X', 'X_CLIENT_ID', 'X_CLIENT_SECRET', 'X_REDIRECT_URI'],
] as const;

const configured = (key: string) => Boolean(process.env[key]?.trim());

export function validateProductionEnvironment() {
  if (process.env.NODE_ENV !== 'production') return;

  const failures: string[] = [];
  const publicUrlValue = process.env.PUBLIC_APP_URL?.trim();
  let publicUrl: URL | undefined;

  if (!publicUrlValue) failures.push('PUBLIC_APP_URL_REQUIRED');
  else {
    try {
      publicUrl = new URL(publicUrlValue);
      if (publicUrl.protocol !== 'https:') failures.push('PUBLIC_APP_URL_HTTPS_REQUIRED');
      if (['localhost', '127.0.0.1', '::1'].includes(publicUrl.hostname)) failures.push('PUBLIC_APP_URL_PUBLIC_HOST_REQUIRED');
      if (publicUrl.pathname !== '/' || publicUrl.search || publicUrl.hash) failures.push('PUBLIC_APP_URL_ORIGIN_REQUIRED');
    } catch { failures.push('PUBLIC_APP_URL_INVALID'); }
  }

  if (process.env.SOCIAL_STORAGE_DRIVER !== 'postgres') failures.push('SOCIAL_STORAGE_DRIVER_POSTGRES_REQUIRED');
  if (!configured('SOCIAL_DATABASE_URL')) failures.push('SOCIAL_DATABASE_URL_REQUIRED');
  if (!configured('SOCIAL_DATABASE_SSL') || process.env.SOCIAL_DATABASE_SSL === 'disable') failures.push('SOCIAL_DATABASE_SSL_REQUIRED');
  try { createTokenCipherFromEnvironment(); } catch { failures.push('SOCIAL_TOKEN_ENCRYPTION_KEY_INVALID'); }

  const callback = publicUrl ? new URL('/api/integrations/oauth/callback', publicUrl).toString() : '';
  for (const [provider, clientKey, secretKey, redirectKey] of providerVariables) {
    const present = [clientKey, secretKey, redirectKey].filter(configured);
    if (present.length > 0 && present.length < 3) failures.push(`${provider}_OAUTH_CONFIGURATION_INCOMPLETE`);
    if (present.length === 3 && process.env[redirectKey]?.trim() !== callback) failures.push(`${provider}_REDIRECT_URI_MISMATCH`);
  }

  const billingVariables = ['STRIPE_SECRET_KEY', 'STRIPE_WEBHOOK_SECRET', 'STRIPE_PRICE_SOLO', 'STRIPE_PRICE_TEAM', 'STRIPE_PRICE_BUSINESS'];
  const billingConfigured = billingVariables.filter(configured);
  if (billingConfigured.length > 0 && billingConfigured.length < billingVariables.length) failures.push('STRIPE_BILLING_CONFIGURATION_INCOMPLETE');

  if (failures.length) throw new Error(`PRODUCTION_CONFIGURATION_INVALID:${failures.join(',')}`);
}

export function requestContext(req: Request, res: Response, next: NextFunction) {
  const candidate = String(req.header('x-request-id') || '');
  const requestId = /^[A-Za-z0-9._:-]{8,128}$/.test(candidate) ? candidate : randomUUID();
  res.locals.requestId = requestId;
  res.setHeader('X-Request-Id', requestId);
  next();
}

export function securityHeaders(_req: Request, res: Response, next: NextFunction) {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  res.setHeader('Permissions-Policy', 'geolocation=(), payment=(), usb=()');
  res.setHeader('Cross-Origin-Opener-Policy', 'same-origin');
  res.setHeader('Cross-Origin-Resource-Policy', 'same-origin');
  if (process.env.NODE_ENV === 'production') {
    res.setHeader('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
    res.setHeader('Content-Security-Policy', "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https:; font-src 'self' data:; connect-src 'self' https:; media-src 'self' blob: https:; worker-src 'self' blob:");
  }
  next();
}
