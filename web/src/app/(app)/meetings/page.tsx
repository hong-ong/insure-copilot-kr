// 회의록(A안): 목록 + 새 회의록(텍스트 입력 → AI가 표준 양식 초안 생성).
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Loader2, Lock, NotebookPen, Search } from "lucide-react";
import { useApp } from "@/components/app/AppContext";
import { api } from "@/lib/api";
import { supabaseBrowser } from "@/lib/supabase/client";
import { TEAM_LABEL, type Team } from "@/lib/types";

interface MeetingRow {
  id: string;
  title: string;
  meeting_date: string;
  team: Team;
  status: "draft" | "confirmed";
  attendees: string[];
  is_sample: boolean;
  summary: { overview?: string; decisions?: string[] } | null;
}

const SAMPLE_TEXT = `상품개정 TF 후속 점검 (예시)

이서연 과장: 영업 가이드에 가입 시기별 도수치료 비교표를 넣었습니다. 2025.07 판과 2026.04 판을 나란히 보여 줍니다.
박지훈 대리: 설명 부족 민원 20건을 분석해 보니 12건이 개정 전 가입자에게 새 한도를 안내한 경우였습니다.
김민준 팀장: 그럼 설계사 대상 공지를 다시 내고, 교육팀에 보수교육 과정 반영을 요청합시다.
김민준 팀장: 결정 사항입니다. 가입 시기별 비교표는 오늘부터 영업 가이드에 반영합니다. 교육팀에 11월 과정 반영을 요청합니다.
김민준 팀장: 박지훈 대리가 11월 7일까지 설계사 공지문 초안을 작성해 주세요.`;

export default function MeetingsPage() {
  const router = useRouter();
  const { profile } = useApp();
  const supabase = supabaseBrowser();
  const [rows, setRows] = useState<MeetingRow[]>([]);
  const [q, setQ] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [title, setTitle] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [visibility, setVisibility] = useState<"all" | "team">("team");
  const [raw, setRaw] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    supabase
      .from("meetings")
      .select("id, title, meeting_date, team, status, attendees, is_sample, summary")
      .order("meeting_date", { ascending: false })
      .limit(100)
      .then(({ data }) => setRows((data as MeetingRow[]) || []));
  }, [supabase]);

  const filtered = useMemo(() => {
    const k = q.trim();
    if (!k) return rows;
    return rows.filter((r) => [r.title, r.summary?.overview, ...(r.summary?.decisions || []), ...r.attendees].join(" ").includes(k));
  }, [rows, q]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await api<{ meeting: { id: string } }>("/meetings", {
        method: "POST",
        json: { title, meeting_date: date, visibility, attendees: [], raw_text: raw },
      });
      router.push(`/meetings/${r.meeting.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "생성 실패");
      setBusy(false);
    }
  }

  return (
    <div className="scrollbar-thin h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-4 py-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h1 className="text-xl font-bold">회의록</h1>
            <p className="mt-1 text-sm text-muted">
              회의 메모·녹취 텍스트를 넣으면 AI가 <b>결정 사항·액션아이템</b>까지 표준 양식으로 정리하고, 확정하면 검색에서 근거로 쓰입니다.
            </p>
          </div>
          {profile?.is_demo ? (
            <span className="inline-flex items-center gap-1 rounded-lg bg-surface px-3 py-2 text-xs text-muted">
              <Lock className="h-3.5 w-3.5" /> 데모는 샘플 회의록 열람만 가능
            </span>
          ) : (
            <button onClick={() => setShowNew((v) => !v)} className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-3 py-2 text-sm font-semibold text-white">
              <NotebookPen className="h-4 w-4" /> 새 회의록
            </button>
          )}
        </div>

        {showNew && (
          <form onSubmit={create} className="mt-4 space-y-3 rounded-2xl border border-line p-5">
            <div className="grid gap-3 sm:grid-cols-3">
              <input required value={title} onChange={(e) => setTitle(e.target.value)} placeholder="회의명" className={`${inputCls} sm:col-span-2`} />
              <input type="date" required value={date} onChange={(e) => setDate(e.target.value)} className={inputCls} />
            </div>
            <div className="flex gap-2">
              {(["team", "all"] as const).map((v) => (
                <button
                  type="button"
                  key={v}
                  onClick={() => setVisibility(v)}
                  className={`h-9 rounded-lg border px-3 text-sm ${visibility === v ? "border-brand bg-brand-soft font-semibold text-brand" : "border-line"}`}
                >
                  {v === "all" ? "전체 공개" : `${profile ? TEAM_LABEL[profile.team] : "팀"}만`}
                </button>
              ))}
            </div>
            <textarea
              required
              minLength={20}
              value={raw}
              onChange={(e) => setRaw(e.target.value)}
              placeholder={"회의 기록을 붙여 넣으세요. '이름: 발언' 형식이면 참석자를 자동으로 찾아요.\n개인정보·건강정보는 자동으로 가려집니다."}
              className="h-56 w-full resize-y rounded-lg border border-line bg-bg p-3 text-sm outline-none focus:border-action"
            />
            <div className="flex flex-wrap items-center justify-between gap-2">
              <button type="button" onClick={() => { setRaw(SAMPLE_TEXT); if (!title) setTitle("상품개정 TF 후속 점검"); }} className="text-xs text-action">
                예시 텍스트 넣기
              </button>
              <button disabled={busy} className="inline-flex h-10 items-center gap-2 rounded-lg bg-brand px-4 text-sm font-semibold text-white disabled:opacity-40">
                {busy && <Loader2 className="h-4 w-4 animate-spin" />} AI로 회의록 초안 만들기
              </button>
            </div>
            {error && <p className="rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>}
          </form>
        )}

        <div className="mt-6 flex items-center gap-2 rounded-lg border border-line px-3">
          <Search className="h-4 w-4 text-muted" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="키워드로 회의록 찾기 (제목·결정 사항·참석자)" className="h-10 flex-1 bg-transparent text-sm outline-none" />
        </div>

        <div className="mt-3 divide-y divide-line rounded-xl border border-line">
          {filtered.length === 0 && <p className="px-4 py-6 text-sm text-muted">회의록이 없어요.</p>}
          {filtered.map((m) => (
            <Link key={m.id} href={`/meetings/${m.id}`} className="block px-4 py-3 hover:bg-surface">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold">{m.title}</span>
                {m.is_sample && <span className="rounded bg-brand-soft px-1.5 py-0.5 text-[10px] font-bold text-brand">샘플</span>}
                <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${m.status === "confirmed" ? "bg-accent-soft text-success" : "bg-warning-soft text-warning"}`}>
                  {m.status === "confirmed" ? "확정 · 검색 반영" : "AI 초안"}
                </span>
              </div>
              <p className="mt-0.5 text-xs text-muted">
                {m.meeting_date} · {TEAM_LABEL[m.team]} · 참석 {m.attendees.length}명
              </p>
              {m.summary?.overview && <p className="mt-1 line-clamp-2 text-sm text-muted">{m.summary.overview}</p>}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

const inputCls = "h-10 w-full rounded-lg border border-line bg-bg px-3 text-sm outline-none focus:border-action";
