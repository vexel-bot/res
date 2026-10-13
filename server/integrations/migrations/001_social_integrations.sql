BEGIN;

CREATE TABLE IF NOT EXISTS clicko_schema_migrations (
  version text PRIMARY KEY,
  applied_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS clicko_social_connections (
  id text PRIMARY KEY,
  owner_type text NOT NULL CHECK (owner_type IN ('personal','workspace')),
  owner_id text NOT NULL,
  client_id text NOT NULL DEFAULT '',
  provider text NOT NULL,
  provider_account_id text NOT NULL,
  data jsonb NOT NULL,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL,
  UNIQUE (owner_type, owner_id, client_id, provider, provider_account_id)
);
CREATE INDEX IF NOT EXISTS clicko_social_connections_owner_idx ON clicko_social_connections(owner_type, owner_id, provider);

CREATE TABLE IF NOT EXISTS clicko_social_oauth_states (
  state_hash text PRIMARY KEY,
  data jsonb NOT NULL,
  expires_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS clicko_social_oauth_states_expiry_idx ON clicko_social_oauth_states(expires_at);

CREATE TABLE IF NOT EXISTS clicko_social_oauth_selections (
  token_hash text PRIMARY KEY,
  owner_type text NOT NULL CHECK (owner_type IN ('personal','workspace')),
  owner_id text NOT NULL,
  actor_id text NOT NULL,
  data jsonb NOT NULL,
  expires_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS clicko_social_oauth_selections_owner_idx ON clicko_social_oauth_selections(owner_type, owner_id, actor_id);

CREATE TABLE IF NOT EXISTS clicko_social_publications (
  id text PRIMARY KEY,
  owner_type text NOT NULL CHECK (owner_type IN ('personal','workspace')),
  owner_id text NOT NULL,
  idempotency_key text NOT NULL,
  data jsonb NOT NULL,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL,
  UNIQUE (owner_type, owner_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS clicko_social_audit_events (
  id text PRIMARY KEY,
  owner_type text NOT NULL CHECK (owner_type IN ('personal','workspace')),
  owner_id text NOT NULL,
  actor_id text NOT NULL,
  provider text NOT NULL,
  action text NOT NULL,
  outcome text NOT NULL,
  data jsonb NOT NULL,
  created_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS clicko_social_audit_owner_idx ON clicko_social_audit_events(owner_type, owner_id, created_at DESC);

INSERT INTO clicko_schema_migrations(version) VALUES ('001_social_integrations') ON CONFLICT(version) DO NOTHING;

COMMIT;
