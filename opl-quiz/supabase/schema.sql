-- ═══════════════════════════════════════════════════════════════════
-- MON NPA — OPL Quiz : recréation de la base Supabase
-- Schéma reconstruit depuis le code de l'app (index.html + fonctions Netlify)
-- À exécuter dans : Supabase → SQL Editor → New query → Run
-- ═══════════════════════════════════════════════════════════════════

-- ── 1. EMPLOYEES ─────────────────────────────────────────────────────
create table public.employees (
  id            uuid primary key default gen_random_uuid(),
  badge_number  text not null unique,
  name          text not null,
  department    text not null default 'WH',
  position      text,
  shift         text,
  is_manager    boolean not null default false,
  is_active     boolean not null default true,
  created_at    timestamptz not null default now()
);

-- ── 2. QUESTIONS ─────────────────────────────────────────────────────
create table public.questions (
  id              uuid primary key default gen_random_uuid(),
  department      text not null,
  wi_reference    text,
  difficulty      text default 'basic',   -- basic | applied | situational
  question_text   text not null,          -- English
  question_th     text,                   -- Thai (version principale)
  option_a        text not null,
  option_b        text not null,
  option_c        text not null,
  option_d        text not null,
  option_a_th     text,
  option_b_th     text,
  option_c_th     text,
  option_d_th     text,
  correct_answer  text not null check (correct_answer in ('A','B','C','D')),
  explanation     text,
  explanation_th  text,
  is_active       boolean not null default false,  -- false = en attente de validation manager
  created_at      timestamptz not null default now()
);

-- ── 3. QUIZ_RESULTS ──────────────────────────────────────────────────
create table public.quiz_results (
  id             uuid primary key default gen_random_uuid(),
  employee_id    uuid references public.employees(id) on delete set null,
  badge_number   text not null,
  employee_name  text,
  department     text,
  score          int not null,
  total          int not null default 3,
  q1_id          uuid,
  q1_answer      text,
  q1_correct     boolean,
  q2_id          uuid,
  q2_answer      text,
  q2_correct     boolean,
  q3_id          uuid,
  q3_answer      text,
  q3_correct     boolean,
  quiz_date      date not null default (now() at time zone 'Asia/Bangkok')::date,
  created_at     timestamptz not null default now()
);

-- Index utiles (le dashboard filtre beaucoup sur ces colonnes)
create index idx_results_date  on public.quiz_results (quiz_date);
create index idx_results_badge on public.quiz_results (badge_number);
create index idx_questions_dept_active on public.questions (department, is_active);

-- ── 4. RLS : politiques permissives pour la clé anon ─────────────────
-- L'app utilise la clé anon directement depuis le navigateur (lecture,
-- écriture, modification, suppression). On reproduit ce comportement.
alter table public.employees    enable row level security;
alter table public.questions    enable row level security;
alter table public.quiz_results enable row level security;

create policy "anon full access" on public.employees    for all to anon using (true) with check (true);
create policy "anon full access" on public.questions    for all to anon using (true) with check (true);
create policy "anon full access" on public.quiz_results for all to anon using (true) with check (true);
