import 'dotenv/config';
import { readFile } from 'node:fs/promises';
import pg from 'pg';

const connectionString = process.env.SOCIAL_DATABASE_URL?.trim();
if (!connectionString) throw new Error('SOCIAL_DATABASE_URL_REQUIRED');
if (process.env.NODE_ENV === 'production' && process.env.SOCIAL_DATABASE_SSL === 'disable') throw new Error('SOCIAL_DATABASE_SSL_REQUIRED');

const sql = await readFile(new URL('../server/integrations/migrations/001_social_integrations.sql', import.meta.url), 'utf8');
const pool = new pg.Pool({
  connectionString,
  ssl: process.env.SOCIAL_DATABASE_SSL === 'disable' ? undefined : { rejectUnauthorized: true },
  max: 1,
  connectionTimeoutMillis: 10_000,
});

try {
  await pool.query(sql);
  console.info('SOCIAL_MIGRATION_COMPLETE', { version: '001_social_integrations' });
} finally {
  await pool.end();
}
