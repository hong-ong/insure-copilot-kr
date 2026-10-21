// 회의록 상세: AI 초안 확인·수정 → 확정(검색 대상 편입). 확정본은 'AI 생성 초안을 누가 확정했는지' 남긴다.
"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { CheckCircle2, Loader2, Plus, Sparkles, Trash2 } from "lucide-react";
import { useApp } from "@/components/app/AppContext";
import { api } from "@/lib/api";
import { supabaseBrowser } from "@/lib/supabase/client";
import { TEAM_LABEL, type Team } from "@/lib/types";

interface ActionItem {
  task: string;
  owner?: string;
  due?: string;
}
interface Summary {
  overview: string;
  agenda: string[];
  decisions: string[];
  action_items: ActionItem[];
  schedule: string[];
  open_issues: string[];
}
interface Meeting {
  id: string;
  title: string;
  meeting_date: string;
  team: Team;
  visibility: string;
  attendees: string[];
  raw_text: string;
  summary: Summary | null;
  status: "draft" | "confirmed";
  document_id: string | null;
  created_by: string | null;
  confirmed_by_name: string | null;
  confirmed_at: string | null;
  is_sample: boolean;
}

const EMPTY: Summary = { overview: "", agenda: [], decisions: [], action_items: [], schedule: [], open_issues: [] };

export default function MeetingDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { profile } = useApp();
  const supabase = supabaseBrowser();
  const [m, setM] = useState<Meeting | null>(null);
  const [s, setS] = useState<Summary>(EMPTY);
  const [saving, setSaving] = useState(false);
  const [showRaw, setShowRaw] = useState(false);

  useEffect(() => {
    supabase
      .from("meetings")
      .select("*")
      .eq("id", id)
      .maybeSingle()
      .then(({ data }) => {
        setM(data as Meeting);
        setS({ ...EMPTY, ...((data as Meeting)?.summary || {}) });
      });
  }, [id, supabase]);

  if (!m) return <Loader2 className="mx-auto mt-20 h-6 w-6 animate-spin text-muted" />;
  const editable = m.status === "draft" && m.created_by === profile?.id && !profile?.is_demo;

  async function save() {
    setSaving(true);
    try {
      await api(`/meetings/${id}`, { method: "PATCH", json: { summary: s } });
    } finally {
      setSaving(false);
    }
  }
  async function confirm() {
    setSaving(true);
    try {
      await api(`/meetings/${id}`, { method: "PATCH", json: { summary: s } });
      const r = await api<{ meeting: Meeting }>(`/meetings/${id}/confirm`, { method: "POST" });
      setM(r.meeting);
    } catch (e) {
      alert(e instanceof Error ? e.message : "확정 실패");
    } finally {
      setSaving(false);
    }
  }

  const list = (key: "agenda" | "decisions" | "schedule" | "open_issues", label: string, ordered = false) => (
    <Section label={label}>
      {editable ? (
        <textarea
          value={s[key].join("\n")}
          onChange={(e) => setS({ ...s, [key]: e.target.value.split("\n") })}
          onBlur={() => setS({ ...s, [key]: s[key].filter((x) => x.trim()) })}
          placeholder="한 줄에 하나씩"
          className="h-24 w-full resize-y rounded-lg border border-line bg-bg p-2 text-sm outline-none focus:border-action"
        />
      ) : s[key].length ? (
        ordered ? (
          <ol className="list-decimal space-y-1 pl-5 text-sm">{s[key].map((x, i) => <li key={i}>{x}</li>)}</ol>
        ) : (
          <ul className="list-disc space-y-1 pl-5 text-sm">{s[key].map((x, i) => <li key={i}>{x}</li>)}</ul>
        )
      ) : (
        <p className="text-sm text-muted">—</p>
      )}
    </Section>
  );

  return (
    <div className="scrollbar-thin h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-4 py-6">
        <Link href="/meetings" className="text-xs text-muted hover:underline">
          ← 회의록 목록
        </Link>
        <h1 className="mt-2 text-xl font-bold">{m.title}</h1>
        <p className="mt-1 text-sm text-muted">
          {m.meeting_date} · {TEAM_LABEL[m.team]} · {m.visibility === "all" ? "전체 공개" : "팀 공개"} · 참석자 {m.attendees.join(", ") || "-"}
        </p>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          {m.status === "confirmed" ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-accent-soft px-2.5 py-1 text-xs font-semibold text-success">
              <CheckCircle2 className="h-3.5 w-3.5" /> 확정 · {m.confirmed_by_name} · 검색 근거로 사용 중
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-warning-soft px-2.5 py-1 text-xs font-semibold text-warning">
              <Sparkles className="h-3.5 w-3.5" /> AI 생성 초안 — 확정 전 내용을 확인하세요
            </span>
          )}
          {m.document_id && (
            <Link href={`/documents/${m.document_id}`} className="rounded-lg border border-line px-2.5 py-1 text-xs hover:bg-surface">
              검색용 문서 보기
            </Link>
          )}
        </div>

        <div className="mt-5 space-y-5 rounded-2xl border border-line p-5">
          <Section label="회의 개요">
            {editable ? (
              <textarea
                value={s.overview}
                onChange={(e) => setS({ ...s, overview: e.target.value })}
                className="h-20 w-full resize-y rounded-lg border border-line bg-bg p-2 text-sm outline-none focus:border-action"
              />
            ) : (
              <p className="text-sm leading-relaxed">{s.overview || "—"}</p>
            )}
          </Section>
          {list("agenda", "주요 안건")}
          {list("decisions", "결정 사항", true)}
          <Section label="액션아이템">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[480px] text-sm">
                <thead className="text-left text-xs text-muted">
                  <tr>
                    <th className="py-1 pr-2">할 일</th>
                    <th className="w-28 py-1 pr-2">담당</th>
                    <th className="w-28 py-1 pr-2">기한</th>
                    {editable && <th className="w-8" />}
                  </tr>
                </thead>
                <tbody>
                  {s.action_items.map((a, i) => (
                    <tr key={i} className="border-t border-line">
                      {(["task", "owner", "due"] as const).map((k) => (
                        <td key={k} className="py-1.5 pr-2 align-top">
                          {editable ? (
                            <input
                              value={a[k] || ""}
                              onChange={(e) => {
                                const items = [...s.action_items];
                                items[i] = { ...items[i], [k]: e.target.value };
                                setS({ ...s, action_items: items });
                              }}
                              className="h-8 w-full rounded border border-line bg-bg px-2 text-sm outline-none focus:border-action"
                            />
                          ) : (
                            a[k] || "-"
                          )}
                        </td>
                      ))}
                      {editable && (
                        <td>
                          <button onClick={() => setS({ ...s, action_items: s.action_items.filter((_, j) => j !== i) })} className="p-1 text-muted hover:text-danger" aria-label="삭제">
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {editable && (
              <button onClick={() => setS({ ...s, action_items: [...s.action_items, { task: "", owner: "", due: "" }] })} className="mt-1 inline-flex items-center gap-1 text-xs text-action">
                <Plus className="h-3 w-3" /> 액션아이템 추가
              </button>
            )}
          </Section>
          {list("schedule", "향후 일정")}
          {list("open_issues", "미결 사항")}
        </div>

        {editable && (
          <div className="mt-4 flex justify-end gap-2">
            <button onClick={save} disabled={saving} className="rounded-lg border border-line px-4 py-2 text-sm hover:bg-surface">
              임시 저장
            </button>
            <button onClick={confirm} disabled={saving} className="inline-flex items-center gap-2 rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-white disabled:opacity-40">
              {saving && <Loader2 className="h-4 w-4 animate-spin" />} 확정하고 검색에 반영
            </button>
          </div>
        )}

        <button onClick={() => setShowRaw((v) => !v)} className="mt-6 text-xs text-action">
          회의 기록 원문 {showRaw ? "닫기" : "보기"} (개인정보 마스킹 적용)
        </button>
        {showRaw && <pre className="mt-2 whitespace-pre-wrap rounded-xl bg-surface p-4 text-xs leading-relaxed">{m.raw_text}</pre>}
      </div>
    </div>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="mb-1.5 text-sm font-bold text-brand">{label}</h2>
      {children}
    </section>
  );
}
