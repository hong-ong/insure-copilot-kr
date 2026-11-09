// 법무팀 판단 문의함: 판단 요구로 거절된 질문이 '법무팀에 문의'로 들어온다 → 답변 등록 → 질문자에게 알림.
"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { Guard, PageHeader } from "@/components/Guard";
import { useApp } from "@/components/app/AppContext";
import { api } from "@/lib/api";
import { supabaseBrowser } from "@/lib/supabase/client";

interface Inquiry {
  id: string;
  question: string;
  status: "open" | "answered";
  answer: string | null;
  created_at: string;
  answered_at: string | null;
}

export default function LegalInquiries() {
  const { profile } = useApp();
  const supabase = supabaseBrowser();
  const [rows, setRows] = useState<Inquiry[] | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [tab, setTab] = useState<"open" | "answered">("open");

  useEffect(() => {
    supabase
      .from("legal_inquiries")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(100)
      .then(({ data }) => setRows((data as Inquiry[]) || []));
  }, [supabase]);

  async function answer(id: string) {
    setBusy(id);
    try {
      const r = await api<{ inquiry: Inquiry }>(`/inquiries/${id}/answer`, { method: "POST", json: { answer: drafts[id] } });
      setRows((list) => list?.map((x) => (x.id === id ? r.inquiry : x)) || null);
    } catch (e) {
      alert(e instanceof Error ? e.message : "실패");
    } finally {
      setBusy(null);
    }
  }

  const shown = (rows || []).filter((r) => r.status === tab);

  return (
    <Guard roles={["legal", "ax_admin"]}>
      <div className="scrollbar-thin h-full overflow-y-auto">
        <div className="mx-auto max-w-3xl px-4 py-6">
          <PageHeader
            title="판단 문의함"
            desc="AI가 '판단은 할 수 없다'며 거절한 질문 중, 질문자가 법무팀 확인을 요청한 건이에요. 답변하면 질문자에게 알림이 갑니다."
            demoReadOnly={profile?.is_demo}
          />
          <div className="mt-4 flex gap-1 rounded-lg bg-surface p-1 text-sm">
            {(["open", "answered"] as const).map((t) => (
              <button key={t} onClick={() => setTab(t)} className={`flex-1 rounded-md py-1.5 ${tab === t ? "bg-bg font-semibold shadow-sm" : "text-muted"}`}>
                {t === "open" ? "답변 대기" : "답변 완료"} ({(rows || []).filter((r) => r.status === t).length})
              </button>
            ))}
          </div>
          {rows === null && <Loader2 className="mx-auto mt-10 h-5 w-5 animate-spin text-muted" />}
          {rows && shown.length === 0 && <p className="mt-6 text-sm text-muted">문의가 없어요.</p>}
          <div className="mt-4 space-y-3">
            {shown.map((r) => (
              <div key={r.id} className="rounded-xl border border-line p-4">
                <p className="text-xs text-muted">{new Date(r.created_at).toLocaleString("ko-KR")}</p>
                <p className="mt-1 font-semibold">“{r.question}”</p>
                {r.status === "answered" ? (
                  <p className="mt-3 whitespace-pre-wrap rounded-lg bg-surface p-3 text-sm">{r.answer}</p>
                ) : (
                  <>
                    <textarea
                      value={drafts[r.id] || ""}
                      onChange={(e) => setDrafts({ ...drafts, [r.id]: e.target.value })}
                      placeholder="근거 조항과 판단 기준을 적어 주세요. 최종 지급 여부는 심사 결과에 따른다는 점을 함께 안내하세요."
                      className="mt-3 h-24 w-full resize-y rounded-lg border border-line bg-bg p-2 text-sm outline-none focus:border-action"
                    />
                    <div className="mt-2 flex justify-end">
                      <button
                        onClick={() => answer(r.id)}
                        disabled={!drafts[r.id]?.trim() || busy === r.id || profile?.is_demo}
                        className="rounded-lg bg-brand px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-40"
                      >
                        답변 보내기
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </Guard>
  );
}
