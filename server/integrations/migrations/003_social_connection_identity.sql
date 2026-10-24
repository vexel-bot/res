BEGIN;

-- A provider identity belongs to one Clicko workspace and can be assigned to
-- only one client at a time. Existing duplicates must be reviewed before this
-- migration; failing the unique index is safer than silently deleting tokens.
CREATE UNIQUE INDEX IF NOT EXISTS clicko_social_connections_identity_idx
  ON clicko_social_connections(owner_type, owner_id, provider, provider_account_id);

INSERT INTO clicko_schema_migrations(version) VALUES ('003_social_connection_identity')
  ON CONFLICT(version) DO NOTHING;

COMMIT;
