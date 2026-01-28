-- HAAIS OS Knowledge Layer Schema
-- Supabase + pgvector
-- Created: 2026-01-23

-- Enable vector extension
create extension if not exists vector;

-- =============================================================================
-- TABLES
-- =============================================================================

-- Departments (tenants)
create table if not exists departments (
  id text primary key,
  name text not null,
  created_at timestamp default now()
);

-- Documents
create table if not exists documents (
  id uuid primary key default gen_random_uuid(),
  department_id text references departments(id) not null,
  title text not null,
  source_path text,
  sha256 text,
  visibility_scope text not null check (visibility_scope in ('private','citywide','shared')) default 'private',
  sensitivity_tier text not null check (sensitivity_tier in ('public','internal','confidential','restricted','privileged')) default 'internal',
  knowledge_profile text,
  shared_with text[] default '{}'::text[],
  created_at timestamp default now(),
  updated_at timestamp default now()
);

-- Chunks with embeddings
create table if not exists document_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid references documents(id) on delete cascade,
  department_id text not null,
  chunk_index int not null,
  heading text,
  content text not null,
  embedding vector(1536),
  metadata jsonb default '{}'::jsonb,
  created_at timestamp default now()
);

-- Query audit logs
create table if not exists kb_query_logs (
  id uuid primary key default gen_random_uuid(),
  at timestamp default now(),
  requester text,
  agent_id text,
  department_id text,
  max_sensitivity text,
  query text,
  retrieved_chunk_ids uuid[],
  retrieved_document_ids uuid[],
  knowledge_profiles_used text[]
);

-- Agent manifests
create table if not exists agent_manifests (
  id uuid primary key default gen_random_uuid(),
  manifest_id text unique not null,
  schema_version text not null,
  manifest jsonb not null,
  is_active boolean default true,
  created_at timestamp default now(),
  updated_at timestamp default now()
);

-- API keys for agents
create table if not exists agent_api_keys (
  id uuid primary key default gen_random_uuid(),
  api_key_hash text unique not null,
  agent_id text not null,
  description text,
  enabled boolean default true,
  last_used_at timestamp,
  created_at timestamp default now()
);

-- =============================================================================
-- INDEXES
-- =============================================================================

create index if not exists document_chunks_embedding_idx
  on document_chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100);

create index if not exists documents_department_idx on documents(department_id);
create index if not exists documents_visibility_idx on documents(visibility_scope);
create index if not exists documents_profile_idx on documents(knowledge_profile);
create index if not exists document_chunks_document_idx on document_chunks(document_id);
create index if not exists document_chunks_department_idx on document_chunks(department_id);
create index if not exists kb_query_logs_at_idx on kb_query_logs(at);
create index if not exists kb_query_logs_requester_idx on kb_query_logs(requester);
create index if not exists kb_query_logs_agent_idx on kb_query_logs(agent_id);

-- =============================================================================
-- ROW LEVEL SECURITY
-- =============================================================================

alter table documents enable row level security;
alter table document_chunks enable row level security;

-- RLS policies for tenant isolation
-- ENTERPRISE CRITICAL: These policies ensure data isolation between tenants

-- Documents: Tenant can only see their own department's documents
-- or citywide/shared documents based on visibility scope
create policy kb_documents_isolation on documents
  for all
  using (
    department_id = current_setting('app.org_id', true)
    or visibility_scope = 'citywide'
    or (visibility_scope = 'shared' and current_setting('app.org_id', true) = any(shared_with))
  )
  with check (department_id = current_setting('app.org_id', true));

-- Document chunks: Follow parent document's department
create policy kb_chunks_isolation on document_chunks
  for all
  using (
    department_id = current_setting('app.org_id', true)
    or department_id in (
      select d.department_id from documents d
      where d.id = document_chunks.document_id
      and (d.visibility_scope = 'citywide'
           or (d.visibility_scope = 'shared' and current_setting('app.org_id', true) = any(d.shared_with)))
    )
  )
  with check (department_id = current_setting('app.org_id', true));

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Basic similarity match with governance filters
create or replace function kb_match_chunks(
  query_embedding vector(1536),
  dept text,
  include_citywide boolean,
  max_sensitivity text,
  match_count int
)
returns table (
  chunk_id uuid,
  document_id uuid,
  title text,
  heading text,
  content text,
  source_path text,
  knowledge_profile text,
  metadata jsonb,
  similarity float
)
language sql stable as $$
  with eligible_docs as (
    select d.*
    from documents d
    where
      (d.department_id = dept
       or (include_citywide and d.visibility_scope = 'citywide')
       or (d.visibility_scope = 'shared' and dept = any(d.shared_with)))
      and (
        case max_sensitivity
          when 'public' then d.sensitivity_tier = 'public'
          when 'internal' then d.sensitivity_tier in ('public','internal')
          when 'confidential' then d.sensitivity_tier in ('public','internal','confidential')
          when 'restricted' then d.sensitivity_tier in ('public','internal','confidential','restricted')
          when 'privileged' then d.sensitivity_tier in ('public','internal','confidential','restricted','privileged')
          else false
        end
      )
  )
  select
    dc.id as chunk_id, dc.document_id, ed.title, dc.heading, dc.content,
    ed.source_path, ed.knowledge_profile, dc.metadata,
    1 - (dc.embedding <=> query_embedding) as similarity
  from document_chunks dc
  join eligible_docs ed on ed.id = dc.document_id
  where dc.embedding is not null
  order by dc.embedding <=> query_embedding
  limit match_count;
$$;

-- Extended match with knowledge profile filtering
create or replace function kb_match_chunks_by_profile(
  query_embedding vector(1536),
  dept text,
  include_citywide boolean,
  max_sensitivity text,
  allowed_profiles text[],
  match_count int
)
returns table (
  chunk_id uuid,
  document_id uuid,
  title text,
  heading text,
  content text,
  source_path text,
  knowledge_profile text,
  metadata jsonb,
  similarity float
)
language sql stable as $$
  with eligible_docs as (
    select d.*
    from documents d
    where
      (d.department_id = dept
       or (include_citywide and d.visibility_scope = 'citywide')
       or (d.visibility_scope = 'shared' and dept = any(d.shared_with)))
      and (allowed_profiles is null
           or array_length(allowed_profiles, 1) is null
           or d.knowledge_profile = any(allowed_profiles))
      and (
        case max_sensitivity
          when 'public' then d.sensitivity_tier = 'public'
          when 'internal' then d.sensitivity_tier in ('public','internal')
          when 'confidential' then d.sensitivity_tier in ('public','internal','confidential')
          when 'restricted' then d.sensitivity_tier in ('public','internal','confidential','restricted')
          when 'privileged' then d.sensitivity_tier in ('public','internal','confidential','restricted','privileged')
          else false
        end
      )
  )
  select
    dc.id as chunk_id, dc.document_id, ed.title, dc.heading, dc.content,
    ed.source_path, ed.knowledge_profile, dc.metadata,
    1 - (dc.embedding <=> query_embedding) as similarity
  from document_chunks dc
  join eligible_docs ed on ed.id = dc.document_id
  where dc.embedding is not null
  order by dc.embedding <=> query_embedding
  limit match_count;
$$;

-- =============================================================================
-- TRIGGERS
-- =============================================================================

create or replace function update_timestamp()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger documents_updated
  before update on documents
  for each row execute function update_timestamp();

create trigger agent_manifests_updated
  before update on agent_manifests
  for each row execute function update_timestamp();
