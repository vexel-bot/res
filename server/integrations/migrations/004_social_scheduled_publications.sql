BEGIN;

CREATE TABLE IF NOT EXISTS clicko_social_scheduled_publications (
  id text PRIMARY KEY,
  owner_type text NOT NULL CHECK (owner_type IN ('personal','workspace')),
  owner_id text NOT NULL,
  connection_id text NOT NULL,
  content_id text NOT NULL,
  scheduled_at timestamptz NOT NULL,
  status text NOT NULL,
  data jsonb NOT NULL,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL,
  UNIQUE(owner_type,owner_id,content_id,connection_id)
);
CREATE INDEX IF NOT EXISTS clicko_social_scheduled_due_idx ON clicko_social_scheduled_publications(scheduled_at) WHERE status='scheduled';
CREATE INDEX IF NOT EXISTS clicko_social_scheduled_stale_idx ON clicko_social_scheduled_publications(updated_at) WHERE status='publishing';
CREATE INDEX IF NOT EXISTS clicko_social_scheduled_owner_idx ON clicko_social_scheduled_publications(owner_type,owner_id,created_at DESC);

INSERT INTO clicko_schema_migrations(version) VALUES ('004_social_scheduled_publications') ON CONFLICT(version) DO NOTHING;

COMMIT;
