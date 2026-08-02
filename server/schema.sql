-- Clicko AI Studios governance schema (PostgreSQL)
create type user_role as enum ('master', 'collaborator');
create type member_status as enum ('active', 'invited', 'disabled');
create type approval_stage as enum ('draft', 'in_review', 'pending_approval', 'approved', 'changes_requested', 'rejected', 'published');

create table plans (
  id text primary key,
  name text not null,
  max_users integer,
  monthly_price numeric(12,2),
  features jsonb not null default '[]'
);

create table workspaces (
  id uuid primary key,
  name text not null,
  logo_url text,
  plan_id text not null references plans(id),
  settings jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table users (
  id uuid primary key,
  workspace_id uuid not null references workspaces(id) on delete cascade,
  email citext not null,
  name text not null,
  avatar_url text,
  role user_role not null default 'collaborator',
  status member_status not null default 'invited',
  password_hash text,
  last_access_at timestamptz,
  created_at timestamptz not null default now(),
  unique (workspace_id, email)
);

create table user_modules (
  workspace_id uuid not null references workspaces(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  module_id text not null,
  created_at timestamptz not null default now(),
  primary key (user_id, module_id)
);

create table invites (
  id uuid primary key,
  workspace_id uuid not null references workspaces(id) on delete cascade,
  email citext not null,
  token_hash text not null unique,
  invited_by uuid not null references users(id),
  expires_at timestamptz not null,
  accepted_at timestamptz,
  created_at timestamptz not null default now()
);

create table subscriptions (
  id uuid primary key,
  workspace_id uuid not null unique references workspaces(id) on delete cascade,
  plan_id text not null references plans(id),
  status text not null,
  provider_customer_id text,
  provider_subscription_id text,
  started_at timestamptz not null,
  renews_at timestamptz,
  updated_at timestamptz not null default now()
);

create table content (
  id uuid primary key,
  workspace_id uuid not null references workspaces(id) on delete cascade,
  author_id uuid not null references users(id),
  title text not null,
  payload jsonb not null,
  approval_stage approval_stage not null default 'draft',
  scheduled_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table content_approvals (
  id uuid primary key,
  workspace_id uuid not null references workspaces(id) on delete cascade,
  content_id uuid not null unique references content(id) on delete cascade,
  approved_by uuid references users(id),
  approved_at timestamptz,
  published_by uuid references users(id),
  published_at timestamptz
);

create table approval_history (
  id uuid primary key,
  workspace_id uuid not null references workspaces(id) on delete cascade,
  approval_id uuid not null references content_approvals(id) on delete cascade,
  actor_id uuid not null references users(id),
  action text not null,
  detail text,
  created_at timestamptz not null default now()
);

create table social_accounts (
  id uuid primary key,
  workspace_id uuid not null references workspaces(id) on delete cascade,
  platform text not null,
  handle text not null,
  credentials_ciphertext text not null,
  created_at timestamptz not null default now()
);

create table notifications (
  id uuid primary key,
  workspace_id uuid not null references workspaces(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  type text not null,
  payload jsonb not null,
  read_at timestamptz,
  created_at timestamptz not null default now()
);

create table audit_logs (
  id uuid primary key,
  workspace_id uuid not null references workspaces(id) on delete cascade,
  actor_id uuid references users(id),
  action text not null,
  resource text not null,
  detail text,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create index users_workspace_idx on users(workspace_id);
create index content_workspace_stage_idx on content(workspace_id, approval_stage);
create index audit_workspace_created_idx on audit_logs(workspace_id, created_at desc);

-- Em produção, aplique Row Level Security em todas as tabelas com workspace_id,
-- usando o workspace autenticado como claim da sessão.
