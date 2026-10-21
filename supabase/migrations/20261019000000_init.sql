-- 가온생명 AX 어시스턴트 — 초기 스키마
-- 권한 원칙: 화면(브라우저)은 RLS가 허용한 행만 읽는다. 쓰기는 대부분 AI 백엔드(service role)가 한다.
-- 검색 함수 match_chunks 는 security invoker → 질문한 사용자의 RLS로 검색된다 (ADR-0002).

create extension if not exists vector with schema extensions;

-- ───────────────────────── 사용자 프로필 ─────────────────────────
-- team: underwriting(심사) claims(지급) education(교육) cs(고객센터) sales(영업) legal(법무) ax(AX)
-- role: agent(설계사) staff(팀원) legal(본사 법무팀) ax_admin(AX 관리자)
create table public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  display_name text not null default '',
  team text not null default 'sales'
    check (team in ('underwriting', 'claims', 'education', 'cs', 'sales', 'legal', 'ax')),
  role text not null default 'agent'
    check (role in ('agent', 'staff', 'legal', 'ax_admin')),
  agent_code text,                -- GenBI 행 단위 권한: 설계사 본인 실적 조회용 (dim_agent.agent_id)
  is_demo boolean not null default false,
  onboarded boolean not null default false,
  ai_notice_agreed_at timestamptz,
  created_at timestamptz not null default now()
);

create or replace function public.my_role() returns text
language sql stable security definer set search_path = public as
$$ select role from public.profiles where id = auth.uid() $$;

create or replace function public.my_team() returns text
language sql stable security definer set search_path = public as
$$ select team from public.profiles where id = auth.uid() $$;

create or replace function public.is_hq() returns boolean
language sql stable security definer set search_path = public as
$$ select coalesce((select role in ('legal', 'ax_admin') from public.profiles where id = auth.uid()), false) $$;

-- ───────────────────────── 문서·버전 ─────────────────────────
create table public.documents (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  doc_type text not null check (doc_type in ('law', 'terms', 'case', 'internal', 'meeting')),
  product text,                                   -- 상품·담보명 (예: 실손의료비)
  visibility text not null default 'all' check (visibility in ('all', 'team')),
  owner_team text not null,
  version_group_id uuid not null default gen_random_uuid(),  -- 같은 문서의 판(버전)을 묶는 ID
  version_label text,                             -- 예: 2026.04 판
  effective_from date,
  effective_to date,                              -- 다음 판이 올라오면 채워짐
  status text not null default 'parsing'
    check (status in ('parsing', 'held', 'rejected', 'active', 'expired')),
  file_name text,
  mime_type text,
  size_bytes integer,
  storage_path text,
  markdown text,                                  -- 원문 뷰어용 파싱 결과
  legal_reviewed_at timestamptz,
  legal_reviewed_by uuid references auth.users (id),
  uploaded_by uuid references auth.users (id),
  created_at timestamptz not null default now()
);
create index on public.documents (version_group_id);
create index on public.documents (status);

create or replace function public.can_read_document(d public.documents) returns boolean
language sql stable security definer set search_path = public as
$$
  select
    case
      when d.status in ('active', 'expired') then
        d.visibility = 'all' or d.owner_team = public.my_team() or public.is_hq()
      else
        d.uploaded_by = auth.uid() or public.is_hq()
    end
$$;

-- 파서 실행 기록 (자동 승인 판정 근거)
create table public.parse_jobs (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents (id) on delete cascade,
  file_format text not null,
  score numeric(5, 4),              -- 한글 인식률 0~1
  ocr_used boolean not null default false,
  verdict text check (verdict in ('approved', 'held', 'rejected')),
  issues jsonb not null default '[]',
  pages integer,
  chars integer,
  chunks integer,
  duration_ms integer,
  created_at timestamptz not null default now()
);

-- 조·항 단위 청크
create table public.chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents (id) on delete cascade,
  chunk_key text not null,          -- 버전이 달라도 같은 조항이면 같은 키 (예: 제4조-2)
  seq integer not null,
  part text not null default '본문', -- 본문 / 특약 / 별표 / 일반
  chapter text,                     -- 관
  article_no text,                  -- 제4조
  article_title text,               -- 보상하는 손해
  paragraph_no text,                -- ②
  heading text,                     -- 화면 표시용 "제4조(보상하는 손해) ②항"
  page integer,
  char_start integer,
  char_end integer,
  text text not null,
  embedding extensions.vector(768),
  created_at timestamptz not null default now()
);
create index on public.chunks (document_id);
create index on public.chunks using hnsw (embedding extensions.vector_cosine_ops);

-- 개정 신구대비표
create table public.document_diffs (
  id uuid primary key default gen_random_uuid(),
  version_group_id uuid not null,
  old_document_id uuid not null references public.documents (id) on delete cascade,
  new_document_id uuid not null references public.documents (id) on delete cascade,
  chunk_key text not null,
  heading text,
  old_text text,
  new_text text,
  change_type text not null check (change_type in ('changed', 'added', 'removed')),
  summary text,                     -- 예: 한도 축소
  created_at timestamptz not null default now()
);

-- ───────────────────────── 대화 ─────────────────────────
create table public.conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  title text not null default '새 대화',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index on public.conversations (user_id, updated_at desc);

create table public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content text not null,            -- 개인정보·건강정보 마스킹 후 저장
  route text check (route in ('rag', 'genbi', 'refuse', 'out_of_scope')),
  refused boolean not null default false,
  model text,
  prompt_tokens integer,
  completion_tokens integer,
  cost_usd numeric(12, 8),          -- 유료 단가 기준 환산 비용 (무료 티어여도 계산)
  latency_ms integer,
  trace_id text,
  meta jsonb not null default '{}',
  created_at timestamptz not null default now()
);
create index on public.messages (conversation_id, created_at);
create index on public.messages (user_id, created_at);

create table public.citations (
  id uuid primary key default gen_random_uuid(),
  message_id uuid not null references public.messages (id) on delete cascade,
  chunk_id uuid references public.chunks (id) on delete set null,
  document_id uuid references public.documents (id) on delete set null,
  chunk_key text,
  label text not null,              -- "실손의료비 특약 · 제4조 ②항 · 2026.04 판"
  rank integer not null
);
create index on public.citations (document_id);

create table public.feedback (
  id uuid primary key default gen_random_uuid(),
  message_id uuid not null references public.messages (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  rating smallint not null check (rating in (-1, 1)),
  reasons text[] not null default '{}',
  comment text,
  review_status text not null default 'open' check (review_status in ('open', 'resolved')),
  correct_answer text,
  promote_to_golden boolean not null default false,
  reviewed_by uuid references auth.users (id),
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  unique (message_id, user_id)
);

-- 판단 요구로 거절된 질문 → 법무팀 문의
create table public.legal_inquiries (
  id uuid primary key default gen_random_uuid(),
  message_id uuid references public.messages (id) on delete set null,
  user_id uuid not null references auth.users (id) on delete cascade,
  question text not null,
  status text not null default 'open' check (status in ('open', 'answered')),
  answer text,
  answered_by uuid references auth.users (id),
  answered_at timestamptz,
  created_at timestamptz not null default now()
);

create table public.notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  body text not null,
  link text,
  read_at timestamptz,
  created_at timestamptz not null default now()
);

-- ───────────────────────── 회의록 ─────────────────────────
create table public.meetings (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  meeting_date date not null,
  team text not null,
  visibility text not null default 'team' check (visibility in ('all', 'team')),
  attendees text[] not null default '{}',
  raw_text text not null,           -- 마스킹 후 저장
  summary jsonb,                    -- {overview, agenda[], decisions[], action_items[{task, owner, due}], schedule[], open_issues[]}
  status text not null default 'draft' check (status in ('draft', 'confirmed')),
  document_id uuid references public.documents (id) on delete set null,  -- 확정 시 검색 대상 문서
  created_by uuid references auth.users (id),
  confirmed_by_name text,
  confirmed_at timestamptz,
  is_sample boolean not null default false,
  created_at timestamptz not null default now()
);

-- ───────────────────────── 평가 ─────────────────────────
create table public.eval_runs (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  config jsonb not null default '{}',
  metrics jsonb not null default '{}',    -- {recall_at_5, mrr, faithfulness, refusal_accuracy, routing_accuracy, p95_ms, cost_per_query}
  notes text,
  created_at timestamptz not null default now()
);

-- ───────────────────────── RLS ─────────────────────────
alter table public.profiles enable row level security;
alter table public.documents enable row level security;
alter table public.parse_jobs enable row level security;
alter table public.chunks enable row level security;
alter table public.document_diffs enable row level security;
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.citations enable row level security;
alter table public.feedback enable row level security;
alter table public.legal_inquiries enable row level security;
alter table public.notifications enable row level security;
alter table public.meetings enable row level security;
alter table public.eval_runs enable row level security;

create policy "본인 프로필" on public.profiles for select using (id = auth.uid() or public.is_hq());

create policy "권한 내 문서" on public.documents for select using (public.can_read_document(documents));

create policy "권한 내 파싱 기록" on public.parse_jobs for select using (
  exists (select 1 from public.documents d where d.id = document_id and public.can_read_document(d))
);

create policy "권한 내 청크" on public.chunks for select using (
  exists (select 1 from public.documents d where d.id = document_id and public.can_read_document(d))
);

create policy "권한 내 신구대비" on public.document_diffs for select using (
  exists (select 1 from public.documents d where d.id = new_document_id and public.can_read_document(d))
);

create policy "본인 대화" on public.conversations for select using (user_id = auth.uid() or public.my_role() = 'ax_admin');
create policy "본인 대화 삭제" on public.conversations for delete using (user_id = auth.uid());
create policy "본인 대화 이름 변경" on public.conversations for update using (user_id = auth.uid());

create policy "본인 메시지" on public.messages for select using (user_id = auth.uid() or public.is_hq());

create policy "본인 메시지 출처" on public.citations for select using (
  exists (select 1 from public.messages m where m.id = message_id and (m.user_id = auth.uid() or public.is_hq()))
);

create policy "피드백 조회" on public.feedback for select using (user_id = auth.uid() or public.is_hq());
create policy "피드백 작성" on public.feedback for insert with check (user_id = auth.uid());
create policy "피드백 수정" on public.feedback for update using (user_id = auth.uid());

create policy "문의 조회" on public.legal_inquiries for select using (user_id = auth.uid() or public.is_hq());

create policy "본인 알림" on public.notifications for select using (user_id = auth.uid());
create policy "본인 알림 읽음" on public.notifications for update using (user_id = auth.uid());

create policy "회의록 조회" on public.meetings for select using (
  is_sample or visibility = 'all' or team = public.my_team() or created_by = auth.uid() or public.is_hq()
);

create policy "평가 조회" on public.eval_runs for select using (public.is_hq());

-- ───────────────────────── 검색 함수 ─────────────────────────
-- security invoker: 호출한 사용자의 RLS가 documents·chunks에 그대로 적용된다.
create or replace function public.match_chunks(
  query_embedding extensions.vector(768),
  match_count integer default 8,
  include_expired boolean default false
)
returns table (
  id uuid,
  document_id uuid,
  chunk_key text,
  heading text,
  part text,
  page integer,
  text text,
  title text,
  doc_type text,
  version_label text,
  version_group_id uuid,
  effective_from date,
  effective_to date,
  doc_status text,
  similarity double precision
)
language sql stable security invoker set search_path = public, extensions as
$$
  select c.id, c.document_id, c.chunk_key, c.heading, c.part, c.page, c.text,
         d.title, d.doc_type, d.version_label, d.version_group_id, d.effective_from, d.effective_to, d.status,
         1 - (c.embedding <=> query_embedding) as similarity
  from public.chunks c
  join public.documents d on d.id = c.document_id
  where c.embedding is not null
    and (d.status = 'active' or (include_expired and d.status = 'expired'))
  order by c.embedding <=> query_embedding
  limit match_count
$$;

-- ───────────────────────── 파일 저장소 ─────────────────────────
insert into storage.buckets (id, name, public, file_size_limit)
values ('documents', 'documents', false, 10485760)  -- 10MB
on conflict (id) do nothing;
