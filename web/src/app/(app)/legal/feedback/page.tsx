// 피드백 검토: 👎 답변을 법무팀이 보고 정답을 기록 → 골든셋 후보로 승격 (품질 개선 루프).
"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { Guard, PageHeader } from "@/components/Guard";
import { useApp } from "@/components/app/AppContext";
import { Markdown } from "@/components/Markdown";
import { api } from "@/lib/api";
import { supabaseBrowser } from "@/lib/supabase/client";
import { ROUTE_LABEL, type Route } from "@/lib/types";

interface Fb {
  id: string;
  rating: number;
  reasons: string[];
  comment: string | null;
  review_status: "open" | "resolved";
  correct_answer: string | null;
  promote_to_golden: boolean;
  created_at: string;
  messages: { id: string; content: string; route: Route; conversation_id: string; created_at: string } | null;
}

export default function FeedbackReview() {
  const { profile } = useApp();
  const supabase = supabaseBrowser();
  const [rows, setRows] = useState<Fb[] | null>(null);
  const [questions, setQuestions] = useState<Record<string, string>>({});
  const [drafts, setDrafts] = useState<Record<string, { answer: string; promote: boolean }>>({});
  const [tab, setTab] = useState<"open" | "resolved">("open");

  useEffect(() => {
    (async () => {
      const { data } = await supabase
        .from("feedback")
        .select("*, messages(id, content, route, conversation_id, created_at)")
        .eq("rating", -1)
        .order("created_at", { ascending: false })
        .limit(100);
      const list = (data as Fb[]) || [];
      setRows(list);
      // 각 답변 바로 앞의 사용자 질문을 찾아 붙인다
      const q: Record<string, string> = {};
      for (const f of list) {
        if (!f.messages) continue;
        const { data: u } = await supabase
          .from("messages")
          .select("content")
          .eq("conversation_id", f.messages.conversation_id)
          .eq("role", "user")
          .lt("created_at", f.messages.created_at)
          .order("created_at", { ascending: false })
          .limit(1);
        if (u?.[0]) q[f.id] = u[0].content;
      }
      setQuestions(q);
    })();
  }, [supabase]);

  async function resolve(id: string) {
    const d = drafts[id] || { answer: "", promote: false };
    const r = await api<{ feedback: Fb }>(`/feedback/${id}/review`, {
      method: "POST",
      json: { correct_answer: d.answer || null, promote_to_golden: d.promote },
    });
    setRows((list) => list?.map((x) => (x.id === id ? { ...x, ...r.feedback } : x)) || null);
  }

  const shown = (rows || []).filter((r) => r.review_status === tab);

  return (
    <Guard roles={["legal", "ax_admin"]}>
      <div className="scrollbar-thin h-full overflow-y-auto">
        <div className="mx-auto max-w-3xl px-4 py-6">
          <PageHeader
            title="피드백 검토"
            desc="사용자가 👎를 누른 답변이에요. 정답을 기록하고 '골든셋 후보'로 올리면 다음 평가 실행에 들어갑니다."
            demoReadOnly={profile?.is_demo}
          />
          <div className="mt-4 flex gap-1 rounded-lg bg-surface p-1 text-sm">
            {(["open", "resolved"] as const).map((t) => (
              <button key={t} onClick={() => setTab(t)} className={`flex-1 rounded-md py-1.5 ${tab === t ? "bg-bg font-semibold shadow-sm" : "text-muted"}`}>
                {t === "open" ? "검토 대기" : "검토 완료"} ({(rows || []).filter((r) => r.review_status === t).length})
              </button>
            ))}
          </div>
          {rows === null && <Loader2 className="mx-auto mt-10 h-5 w-5 animate-spin text-muted" />}
          {rows && shown.length === 0 && <p className="mt-6 text-sm text-muted">피드백이 없어요.</p>}
          <div className="mt-4 space-y-3">
            {shown.map((f) => (
              <div key={f.id} className="rounded-xl border border-line p-4">
                <div className="flex flex-wrap items-center gap-1.5">
                  {f.messages && <span className="rounded-full bg-brand-soft px-2 py-0.5 text-[11px] font-semibold text-brand">{ROUTE_LABEL[f.messages.route] || "-"}</span>}
                  {f.reasons.map((r) => (
                    <span key={r} className="rounded-full bg-danger-soft px-2 py-0.5 text-[11px] font-semibold text-danger">
                      {r}
                    </span>
                  ))}
                  <span className="ml-auto text-[11px] text-muted">{new Date(f.created_at).toLocaleString("ko-KR")}</span>
                </div>
                {questions[f.id] && <p className="mt-2 text-sm font-semibold">Q. {questions[f.id]}</p>}
                {f.messages && (
                  <div className="mt-2 max-h-48 overflow-y-auto rounded-lg bg-surface p-3 text-sm">
                    <Markdown>{f.messages.content}</Markdown>
                  </div>
                )}
                {f.comment && <p className="mt-2 text-sm text-muted">사용자 의견: {f.comment}</p>}
                {f.review_status === "resolved" ? (
                  <div className="mt-3 text-sm">
                    {f.correct_answer && <p className="whitespace-pre-wrap rounded-lg border border-line p-3">정답: {f.correct_answer}</p>}
                    {f.promote_to_golden && <p className="mt-1 text-xs font-semibold text-success">골든셋 후보로 승격됨</p>}
                  </div>
                ) : (
                  <div className="mt-3">
                    <textarea
                      value={drafts[f.id]?.answer || ""}
                      onChange={(e) => setDrafts({ ...drafts, [f.id]: { answer: e.target.value, promote: drafts[f.id]?.promote || false } })}
                      placeholder="정답(근거 조항 포함)을 기록하세요"
                      className="h-20 w-full resize-y rounded-lg border border-line bg-bg p-2 text-sm outline-none focus:border-action"
                    />
                    <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                      <label className="flex items-center gap-1.5 text-xs">
                        <input
                          type="checkbox"
                          checked={drafts[f.id]?.promote || false}
                          onChange={(e) => setDrafts({ ...drafts, [f.id]: { answer: drafts[f.id]?.answer || "", promote: e.target.checked } })}
                        />
                        골든셋 후보로 올리기
                      </label>
                      <button onClick={() => resolve(f.id)} disabled={profile?.is_demo} className="rounded-lg bg-brand px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-40">
                        검토 완료
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </Guard>
  );
}
