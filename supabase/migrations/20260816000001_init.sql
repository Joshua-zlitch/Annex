-- ============================================================================
-- ANNEX - "Learn Before You Believe" media & information literacy platform
-- Phase 1 database schema (Postgres on Supabase).
-- Apply via: supabase db push  (or run manually in the SQL editor)
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------
create type public.media_type as enum ('image', 'video', 'audio', 'document', 'text', 'url');
create type public.media_source as enum ('upload', 'url', 'text');
create type public.analysis_status as enum ('pending', 'processing', 'completed', 'failed');

-- ---------------------------------------------------------------------------
-- media
-- ---------------------------------------------------------------------------
create table public.media (
    id            uuid primary key default gen_random_uuid(),
    owner_id      uuid not null references auth.users (id) on delete cascade,
    media_type    public.media_type not null,
    source        public.media_source not null,
    storage_path  text,
    source_url    text,
    text_content  text,
    filename      text,
    mime_type     text,
    created_at    timestamptz not null default now()
);

create index media_owner_created_idx on public.media (owner_id, created_at desc);

-- ---------------------------------------------------------------------------
-- analysis
-- ---------------------------------------------------------------------------
create table public.analysis (
    id                uuid primary key default gen_random_uuid(),
    media_id          uuid not null references public.media (id) on delete cascade,
    owner_id          uuid not null references auth.users (id) on delete cascade,
    status            public.analysis_status not null default 'pending',
    ocr_text          text,
    summary           text,
    credibility_score numeric,
    confidence        numeric,
    flagged           boolean not null default false,
    reasoning         text,
    error             text,
    created_at        timestamptz not null default now(),
    completed_at      timestamptz
);

create index analysis_media_created_idx on public.analysis (media_id, created_at desc);
create index analysis_owner_created_idx on public.analysis (owner_id, created_at desc);

-- ---------------------------------------------------------------------------
-- claims (extracted assertions from an analysis)
-- ---------------------------------------------------------------------------
create table public.claims (
    id          uuid primary key default gen_random_uuid(),
    analysis_id uuid not null references public.analysis (id) on delete cascade,
    owner_id    uuid not null references auth.users (id) on delete cascade,
    text        text not null,
    position    integer not null default 0,
    created_at  timestamptz not null default now()
);

create index claims_analysis_position_idx on public.claims (analysis_id, position);

-- ---------------------------------------------------------------------------
-- Row level security: users can only access their own data.
-- ---------------------------------------------------------------------------
alter table public.media    enable row level security;
alter table public.analysis enable row level security;
alter table public.claims   enable row level security;

create policy "media_select_own" on public.media
    for select using (auth.uid() = owner_id);
create policy "media_insert_own" on public.media
    for insert with check (auth.uid() = owner_id);

create policy "analysis_select_own" on public.analysis
    for select using (auth.uid() = owner_id);
create policy "analysis_insert_own" on public.analysis
    for insert with check (auth.uid() = owner_id);

create policy "claims_select_own" on public.claims
    for select using (auth.uid() = owner_id);
create policy "claims_insert_own" on public.claims
    for insert with check (auth.uid() = owner_id);

-- ---------------------------------------------------------------------------
-- Storage bucket for raw media (service role uploads / reads bypass RLS).
-- ---------------------------------------------------------------------------
insert into storage.buckets (id, name, public)
values ('annex-media', 'annex-media', false)
on conflict (id) do nothing;

create policy "annex_media_storage_read" on storage.objects
    for select using (bucket_id = 'annex-media' and auth.uid() = (storage.foldername(name))[1]::uuid);
create policy "annex_media_storage_write" on storage.objects
    for insert with check (bucket_id = 'annex-media' and auth.uid() = (storage.foldername(name))[1]::uuid);