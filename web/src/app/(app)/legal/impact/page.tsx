// 개정 영향 분석: 개정으로 바뀐 조항을 근거로 인용했던 과거 답변을 찾아, 질문자에게 재안내 알림을 보낸다.
"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { BellRing, FileDiff, Loader2 } from "lucide-react";
import { Guard, PageHeader } from "@/components/Guard";
import { useApp } from "@/components/app/AppContext";
import { api } from "@/lib/api";
import { supabaseBrowser } from "@/lib/supabase/client";

interface Revision {
  id: string;
  title: string;
  version_label: string | null;
  effective_from: string | null;
  legal_reviewed_at: string | null;
}
interface Impact {
  changed_clauses: string[];
  messages: { message_id: string; created_at: string; answer: string; labels: string[] }[];
}

function ImpactInner() {
  const { profile } = useApp();
  const params = useSearchParams();
  const supabase = supabaseBrowser();
  const [revisions, setRevisions] = useState<Revision[]>([]);
  const [selected, setSelected] = useState<string | null>(params.get("doc"));
  const [impact, setImpact] = useState<Impact | null>(null);
  const [loading, setLoading] = useState(false);
  const [notified, setNotified] = useState<number | null>(null);

  useEffect(() => {
    (async () => {
      const { data } = await supabase.from("document_diffs").select("new_document_id");
      const ids = Array.from(new Set((data || []).map((d: { new_document_id: string }) => d.new_document_id)));
      if (!ids.length) return;
      const { data: docs } = await supabase
        .from("documents")
        .select("id, title, version_label, effective_from, legal_reviewed_at")
        .in("id", ids)
        .order("created_at", { ascending: false });
      setRevisions((docs as Revision[]) || []);
      if (!selected && docs?.[0]) setSelected(docs[0].id);
    })();
  }, [supabase, selected]);

  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    setNotified(null);
    api<Impact>(`/documents/${selected}/impact`)
      .then(setImpact)
      .catch(() => setImpact(null))
      .finally(() => setLoading(false));
  }, [selected]);

  async function notify() {
    if (!selected) return;
    try {
      const r = await api<{ notified: number }>(`/documents/${selected}/impact/notify`, { method: "POST" });
      setNotified(r.notified);
    } catch (e) {
      alert(e instanceof Error ? e.message : "실패");
    }
  }

  return (
    <div className="scrollbar-thin h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-4 py-6">
        <PageHeader
          title="개정 영향 분석"
          desc="약관이 개정되면, 바뀐 조항을 근거로 이미 안내된 답변이 있는지 찾아 질문자에게 다시 확인하라고 알립니다. (리스크: 약관 개정 반영 지연)"
          demoReadOnly={profile?.is_demo}
        />
        <div className="mt-4 flex flex-wrap gap-2">
          {revisions.length === 0 && <p className="text-sm text-muted">개정안(새 판)으로 올라온 문서가 없어요.</p>}
          {revisions.map((r) => (
            <button
              key={r.id}
              onClick={() => setSelected(r.id)}
              className={`rounded-lg border px-3 py-2 text-left text-sm ${selected === r.id ? "border-brand bg-brand-soft" : "border-line hover:bg-surface"}`}
            >
              <span className="block font-semibold">{r.title}</span>
              <span className="text-xs text-muted">
                {r.version_label} · {r.legal_reviewed_at ? "검토 완료" : "검토 대기"}
              </span>
            </button>
          ))}
        </div>

        {loading && <Loader2 className="mx-auto mt-10 h-5 w-5 animate-spin text-muted" />}
        {impact && !loading && selected && (
          <div className="mt-6 space-y-4">
            <div className="rounded-xl border border-line p-4">
              <div className="flex items-center justify-between">
                <p className="text-sm font-bold">바뀐 조항 {impact.changed_clauses.length}건</p>
                <Link href={`/documents/${selected}/diff`} className="inline-flex items-center gap-1 text-xs text-action">
                  <FileDiff className="h-3.5 w-3.5" /> 신구대비표
                </Link>
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {impact.changed_clauses.map((c) => (
                  <span key={c} className="rounded-full bg-warning-soft px-2 py-0.5 text-xs text-warning">
                    {c}
                  </span>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-line p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-bold">바뀐 조항을 근거로 인용했던 과거 답변 {impact.messages.length}건</p>
                {notified !== null ? (
                  <span className="text-xs font-semibold text-success">질문자 {notified}명에게 개정 안내를 보냈어요.</span>
                ) : (
                  <button
                    onClick={notify}
                    disabled={!impact.messages.length || profile?.is_demo}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40"
                  >
                    <BellRing className="h-3.5 w-3.5" /> 질문자에게 개정 안내 보내기
                  </button>
                )}
              </div>
              {impact.messages.length === 0 && <p className="mt-2 text-sm text-muted">이전 판 조항을 인용한 답변이 아직 없어요.</p>}
              <div className="mt-3 divide-y divide-line">
                {impact.messages.map((m) => (
                  <div key={m.message_id} className="py-2.5 text-sm">
                    <p className="text-xs text-muted">{new Date(m.created_at).toLocaleString("ko-KR")}</p>
                    <p className="mt-0.5 line-clamp-2">{m.answer}</p>
                    <p className="mt-1 text-xs text-warning">{Array.from(new Set(m.labels)).join(" · ")}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ImpactPage() {
  return (
    <Guard roles={["legal", "ax_admin"]}>
      <Suspense>
        <ImpactInner />
      </Suspense>
    </Guard>
  );
}
