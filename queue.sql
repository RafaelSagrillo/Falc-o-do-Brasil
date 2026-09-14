create table public.pdf_processing_jobs (
 id uuid primary key default gen_random_uuid(),
 object_id uuid not null,
 object_version text not null,
 bucket_id text not null check(bucket_id in ('falcao-documentos','familia-documentos')),
 object_path text not null,
 status text not null default 'queued' check(status in ('queued','processing','done','needs_review','failed','superseded')),
 attempts integer not null default 0,
 lease_token uuid,
 leased_until timestamptz,
 available_at timestamptz not null default now(),
 created_at timestamptz not null default now(),
 finished_at timestamptz,
 document_id uuid references public.pdf_documents(id),
 error_code text,
 unique(object_id,object_version)
);
create index pdf_processing_jobs_ready_idx on public.pdf_processing_jobs(status,available_at);
alter table public.pdf_processing_jobs enable row level security;
revoke all on public.pdf_processing_jobs from anon,authenticated;
comment on table public.pdf_processing_jobs is 'Fila privada. Descoberta por polling do worker Python; versao de objeto evita reprocessamento. Sem worker hospedado, nao ha processamento automatico.';
