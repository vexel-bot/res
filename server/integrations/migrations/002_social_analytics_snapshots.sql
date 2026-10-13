BEGIN;

CREATE TABLE IF NOT EXISTS clicko_social_analytics_snapshots (
  owner_type text NOT NULL CHECK (owner_type IN ('personal','workspace')),
  owner_id text NOT NULL,
  connection_id text NOT NULL REFERENCES clicko_social_connections(id) ON DELETE CASCADE,
  period_from date NOT NULL,
  period_to date NOT NULL,
  data jsonb NOT NULL,
  updated_at timestamptz NOT NULL,
  PRIMARY KEY (owner_type, owner_id, connection_id, period_from, period_to)
);
CREATE INDEX IF NOT EXISTS clicko_social_analytics_owner_idx ON clicko_social_analytics_snapshots(owner_type,owner_id,updated_at DESC);
INSERT INTO clicko_schema_migrations(version) VALUES ('002_social_analytics_snapshots') ON CONFLICT(version) DO NOTHING;

COMMIT;
