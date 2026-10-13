import test from 'node:test';
import assert from 'node:assert/strict';
import { validateProductionEnvironment } from './production';

const keys = [
  'NODE_ENV', 'PUBLIC_APP_URL', 'SOCIAL_STORAGE_DRIVER', 'SOCIAL_DATABASE_URL',
  'SOCIAL_DATABASE_SSL', 'SOCIAL_TOKEN_ENCRYPTION_KEY', 'META_APP_ID',
  'META_APP_SECRET', 'META_REDIRECT_URI',
  'STRIPE_SECRET_KEY', 'STRIPE_WEBHOOK_SECRET', 'STRIPE_PRICE_SOLO', 'STRIPE_PRICE_TEAM', 'STRIPE_PRICE_BUSINESS',
];

function withEnvironment(values: Record<string, string | undefined>, action: () => void) {
  const previous = new Map(keys.map(key => [key, process.env[key]]));
  try {
    keys.forEach(key => delete process.env[key]);
    Object.entries(values).forEach(([key, value]) => value === undefined ? delete process.env[key] : process.env[key] = value);
    action();
  } finally {
    previous.forEach((value, key) => value === undefined ? delete process.env[key] : process.env[key] = value);
  }
}

const valid = {
  NODE_ENV: 'production',
  PUBLIC_APP_URL: 'https://app.example.test',
  SOCIAL_STORAGE_DRIVER: 'postgres',
  SOCIAL_DATABASE_URL: 'postgresql://database.example.test/clicko',
  SOCIAL_DATABASE_SSL: 'require',
  SOCIAL_TOKEN_ENCRYPTION_KEY: Buffer.alloc(32, 5).toString('base64url'),
};

test('production environment accepts a secure PostgreSQL configuration', () => {
  withEnvironment(valid, () => assert.doesNotThrow(validateProductionEnvironment));
});

test('production environment rejects localhost and a non-PostgreSQL store', () => {
  withEnvironment({ ...valid, PUBLIC_APP_URL: 'http://localhost:3000', SOCIAL_STORAGE_DRIVER: 'json' }, () => {
    assert.throws(validateProductionEnvironment, /PUBLIC_APP_URL_HTTPS_REQUIRED.*PUBLIC_APP_URL_PUBLIC_HOST_REQUIRED.*SOCIAL_STORAGE_DRIVER_POSTGRES_REQUIRED/);
  });
});

test('production environment rejects partial provider credentials and callback drift', () => {
  withEnvironment({ ...valid, META_APP_ID: 'configured', META_APP_SECRET: 'configured', META_REDIRECT_URI: 'https://other.example.test/api/integrations/oauth/callback' }, () => {
    assert.throws(validateProductionEnvironment, /META_REDIRECT_URI_MISMATCH/);
  });
  withEnvironment({ ...valid, META_APP_ID: 'configured' }, () => {
    assert.throws(validateProductionEnvironment, /META_OAUTH_CONFIGURATION_INCOMPLETE/);
  });
});

test('production environment rejects a partial billing configuration', () => {
  withEnvironment({ ...valid, STRIPE_SECRET_KEY: 'configured' }, () => {
    assert.throws(validateProductionEnvironment, /STRIPE_BILLING_CONFIGURATION_INCOMPLETE/);
  });
  withEnvironment({ ...valid, STRIPE_SECRET_KEY: 'configured', STRIPE_WEBHOOK_SECRET: 'configured', STRIPE_PRICE_SOLO: 'price_solo', STRIPE_PRICE_TEAM: 'price_team', STRIPE_PRICE_BUSINESS: 'price_business' }, () => {
    assert.doesNotThrow(validateProductionEnvironment);
  });
});
