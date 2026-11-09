// 개정 신구대비표: 구 판 / 신 판 / 변경 꼬리표. 법무팀은 검토 완료 표시를 남길 수 있다.
"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { CheckCircle2, FileDiff, Loader2 } from "lucide-react";
import { useApp } from "@/components/app/AppContext";
import { api } from "@/lib/api";
import { supabaseBrowser } from "@/lib/supabase/client";

interface Diff {
  id: string;
  chunk_key: string;
  heading: string;
  old_text: string | null;
  new_text: string | null;
  change_type: "changed" | "added" | "removed";
  summary: string | null;
  old_document_id: string;
}

interface DocInfo {
  id: string;
  title: string;
  version_label: string | null;
  effective_from: string | null;
  legal_reviewed_at: string | null;
}

const TYPE_STYLE = {
  changed: "bg-warning-soft text-warning",
  added: "bg-accent-soft text-success",
  removed: "bg-danger-soft text-danger",
};

function stripHead(t: string | null) {
  // 청크 앞에 붙여 둔 조 제목 줄(### 제4조(...))은 표에서 빼고 본문만 보인다
  return (t || "").replace(/^#+\s*제\s*\d+\s*조[^\n]*\n?/, "").trim();
}

export default function DiffPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { profile } = useApp();
  const supabase = supabaseBrowser();
  const [diffs, setDiffs] = useState<Diff[] | null>(null);
  const [newDoc, setNewDoc] = useState<DocInfo | null>(null);
  const [oldDoc, setOldDoc] = useState<DocInfo | null>(null);
  const [reviewing, setReviewing] = useState(false);

  useEffect(() => {
    (async () => {
      const { data: nd } = await supabase
        .from("documents")
        .select("id, title, version_label, effective_from, legal_reviewed_at")
        .eq("id", id)
        .maybeSingle();
      setNewDoc(nd as DocInfo);
      const { data } = await supabase.from("document_diffs").select("*").eq("new_document_id", id);
      const rows = (data as Diff[]) || [];
      const order = (k: string) => {
        const m = k.match(/제(\d+)조(?:-(\d+))?/);
        return m ? Number(m[1]) * 100 + Number(m[2] || 0) : 99999;
      };
      rows.sort((a, b) => order(a.chunk_key) - order(b.chunk_key));
      setDiffs(rows);
      if (rows[0]) {
        const { data: od } = await supabase
          .from("documents")
          .select("id, title, version_label, effective_from, legal_reviewed_at")
          .eq("id", rows[0].old_document_id)
          .maybeSingle();
        setOldDoc(od as DocInfo);
      }
    })();
  }, [id, supabase]);

  async function markReviewed() {
    setReviewing(true);
    try {
      const r = await api<{ legal_reviewed_at: string }>(`/documents/${id}/legal-review`, { method: "POST" });
      setNewDoc((d) => (d ? { ...d, legal_reviewed_at: r.legal_reviewed_at } : d));
    } catch (e) {
      alert(e instanceof Error ? e.message : "실패");
    } finally {
      setReviewing(false);
    }
  }

  const isHq = profile?.role === "legal" || profile?.role === "ax_admin";

  return (
    <div className="scrollbar-thin h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl px-4 py-6">
        <p className="flex items-center gap-1.5 text-xs font-semibold text-muted">
          <FileDiff className="h-4 w-4" /> 신구대비표 (자동 생성)
        </p>
        <h1 className="mt-1 text-xl font-bold">{newDoc?.title || "…"}</h1>
        {oldDoc && newDoc && (
          <p className="mt-1 text-sm text-muted">
            <Link href={`/documents/${oldDoc.id}`} className="underline">
              {oldDoc.version_label || "이전 판"}
            </Link>{" "}
            →{" "}
            <Link href={`/documents/${newDoc.id}`} className="font-semibold text-brand underline">
              {newDoc.version_label || "새 판"}
            </Link>{" "}
            · 변경 조항 {diffs?.length ?? 0}건 · {newDoc.effective_from} 이후 체결 계약부터 적용
          </p>
        )}

        <div className="mt-3 flex flex-wrap items-center gap-2">
          {newDoc?.legal_reviewed_at ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-accent-soft px-2.5 py-1 text-xs font-semibold text-success">
              <CheckCircle2 className="h-3.5 w-3.5" /> 법무팀 검토 완료 · {new Date(newDoc.legal_reviewed_at).toLocaleDateString("ko-KR")}
            </span>
          ) : (
            <span className="rounded-full bg-warning-soft px-2.5 py-1 text-xs font-semibold text-warning">법무팀 검토 대기</span>
          )}
          {isHq && !newDoc?.legal_reviewed_at && (
            <button
              onClick={markReviewed}
              disabled={reviewing || profile?.is_demo}
              title={profile?.is_demo ? "데모 계정은 읽기 전용이에요" : undefined}
              className="rounded-lg bg-brand px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40"
            >
              검토 완료 표시
            </button>
          )}
          {isHq && (
            <Link href={`/legal/impact?doc=${id}`} className="rounded-lg border border-line px-3 py-1.5 text-xs hover:bg-surface">
              개정 영향 분석 →
            </Link>
          )}
        </div>

        {diffs === null && <Loader2 className="mx-auto mt-10 h-5 w-5 animate-spin text-muted" />}
        {diffs?.length === 0 && <p className="mt-8 text-sm text-muted">이전 판과 비교할 변경 내용이 없어요. (개정안으로 올린 문서에만 신구대비표가 생깁니다)</p>}

        {diffs && diffs.length > 0 && (
          <div className="mt-5 overflow-x-auto rounded-xl border border-line">
            <table className="w-full min-w-[720px] text-sm">
              <thead className="bg-surface text-left text-xs text-muted">
                <tr>
                  <th className="w-44 px-3 py-2">조항</th>
                  <th className="px-3 py-2">구 ({oldDoc?.version_label || "이전 판"})</th>
                  <th className="px-3 py-2">신 ({newDoc?.version_label || "새 판"})</th>
                  <th className="w-28 px-3 py-2">변경</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line align-top">
                {diffs.map((d) => (
                  <tr key={d.id}>
                    <td className="px-3 py-3 text-xs font-semibold">
                      <Link href={`/documents/${id}?key=${encodeURIComponent(d.chunk_key)}`} className="hover:underline">
                        {d.heading}
                      </Link>
                    </td>
                    <td className="whitespace-pre-wrap px-3 py-3 text-xs leading-relaxed text-muted">{stripHead(d.old_text) || "—"}</td>
                    <td className="whitespace-pre-wrap px-3 py-3 text-xs leading-relaxed">{stripHead(d.new_text) || "(삭제)"}</td>
                    <td className="px-3 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${TYPE_STYLE[d.change_type]}`}>{d.summary}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
