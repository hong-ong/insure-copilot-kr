// 원문 뷰어: 출처 칩을 누르면 해당 문서를 열고, 인용된 조항 위치로 스크롤해 노란색으로 표시한다.
"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { AlertTriangle, Download, ExternalLink, FileDiff, Loader2, X } from "lucide-react";
import { Markdown } from "@/components/Markdown";
import { supabaseBrowser } from "@/lib/supabase/client";
import { api } from "@/lib/api";
import { DOC_TYPE_LABEL } from "@/lib/types";

interface Doc {
  id: string;
  title: string;
  doc_type: string;
  version_label: string | null;
  version_group_id: string;
  effective_from: string | null;
  effective_to: string | null;
  status: string;
  markdown: string | null;
  file_name: string | null;
}

interface ChunkPos {
  char_start: number;
  char_end: number;
  heading: string;
}

const PAGE_BREAK = "\f";

function render(text: string) {
  // 약관은 한 줄에 한 항(①②③)이라, 마크다운이 줄바꿈 하나를 공백으로 합치지 않게 강제 줄바꿈으로 바꾼다
  return text
    .split(PAGE_BREAK)
    .join("\n\n---\n\n")
    .replace(/([^\n])\n(?!\n)/g, "$1  \n");
}

export function DocumentViewer({
  documentId,
  chunkId,
  chunkKey,
  onClose,
  fullPage = false,
}: {
  documentId: string;
  chunkId?: string | null;
  chunkKey?: string | null;
  onClose?: () => void;
  fullPage?: boolean;
}) {
  const [doc, setDoc] = useState<Doc | null>(null);
  const [pos, setPos] = useState<ChunkPos | null>(null);
  const [hasDiff, setHasDiff] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const markRef = useRef<HTMLDivElement>(null);
  const supabase = supabaseBrowser();

  useEffect(() => {
    let cancelled = false;
    setDoc(null);
    setPos(null);
    setError(null);
    (async () => {
      const { data, error } = await supabase
        .from("documents")
        .select("id, title, doc_type, version_label, version_group_id, effective_from, effective_to, status, markdown, file_name")
        .eq("id", documentId)
        .maybeSingle();
      if (cancelled) return;
      if (error || !data) {
        setError("문서를 볼 권한이 없거나 문서가 없어요.");
        return;
      }
      setDoc(data as Doc);
      let q = supabase.from("chunks").select("char_start, char_end, heading").eq("document_id", documentId);
      if (chunkId) q = q.eq("id", chunkId);
      else if (chunkKey) q = q.eq("chunk_key", chunkKey);
      else q = q.limit(0);
      const { data: c } = await q.limit(1);
      if (!cancelled && c && c[0]) setPos(c[0] as ChunkPos);
      const { count } = await supabase
        .from("document_diffs")
        .select("id", { count: "exact", head: true })
        .eq("new_document_id", documentId);
      if (!cancelled) setHasDiff((count || 0) > 0);
    })();
    return () => {
      cancelled = true;
    };
  }, [documentId, chunkId, chunkKey, supabase]);

  useEffect(() => {
    if (pos && markRef.current) markRef.current.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [pos, doc]);

  async function download() {
    try {
      const r = await api<{ url: string }>(`/documents/${documentId}/download`);
      window.open(r.url, "_blank");
    } catch (e) {
      alert(e instanceof Error ? e.message : "다운로드 실패");
    }
  }

  const md = doc?.markdown || "";
  const hasPos = pos && pos.char_end > pos.char_start && pos.char_end <= md.length + 5;
  const before = hasPos ? md.slice(0, pos!.char_start) : md;
  const marked = hasPos ? md.slice(pos!.char_start, pos!.char_end) : "";
  const after = hasPos ? md.slice(pos!.char_end) : "";

  return (
    <div className={`flex h-full flex-col bg-bg ${fullPage ? "" : "border-l border-line"}`}>
      <div className="flex items-start gap-2 border-b border-line px-4 py-3">
        <div className="min-w-0 flex-1">
          {doc ? (
            <>
              <p className="text-[11px] font-semibold text-muted">{DOC_TYPE_LABEL[doc.doc_type] || doc.doc_type}</p>
              <h2 className="truncate text-sm font-bold" title={doc.title}>
                {doc.title}
              </h2>
              <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px]">
                {doc.version_label && <span className="rounded bg-brand-soft px-1.5 py-0.5 font-semibold text-brand">{doc.version_label}</span>}
                <span className="text-muted">
                  적용 {doc.effective_from || "?"} ~ {doc.effective_to || "현재"}
                </span>
                {doc.status === "expired" && (
                  <span className="rounded bg-warning-soft px-1.5 py-0.5 font-semibold text-warning">구버전</span>
                )}
              </div>
              {pos && <p className="mt-1 text-xs text-muted">인용 위치: {pos.heading}</p>}
            </>
          ) : (
            <p className="text-sm text-muted">{error || "불러오는 중…"}</p>
          )}
        </div>
        {onClose && (
          <button onClick={onClose} className="rounded-md p-1 text-muted hover:bg-surface" aria-label="닫기">
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      {doc && (
        <div className="flex flex-wrap gap-2 border-b border-line px-4 py-2 text-xs">
          {!fullPage && (
            <Link
              href={`/documents/${doc.id}${chunkId ? `?chunk=${chunkId}` : ""}`}
              target="_blank"
              className="inline-flex items-center gap-1 rounded-md border border-line px-2 py-1 hover:bg-surface"
            >
              <ExternalLink className="h-3.5 w-3.5" /> 새 탭에서 열기
            </Link>
          )}
          {hasDiff && (
            <Link href={`/documents/${doc.id}/diff`} className="inline-flex items-center gap-1 rounded-md border border-line px-2 py-1 hover:bg-surface">
              <FileDiff className="h-3.5 w-3.5" /> 신구대비표
            </Link>
          )}
          {doc.file_name && (
            <button onClick={download} className="inline-flex items-center gap-1 rounded-md border border-line px-2 py-1 hover:bg-surface">
              <Download className="h-3.5 w-3.5" /> 원본 파일
            </button>
          )}
        </div>
      )}

      {doc?.status === "expired" && (
        <div className="mx-4 mt-3 flex gap-2 rounded-lg bg-warning-soft px-3 py-2 text-xs text-warning">
          <AlertTriangle className="h-4 w-4 shrink-0" />이 문서는 개정 전 판입니다. 해당 기간 가입 계약에만 적용돼요.
        </div>
      )}

      <div className="scrollbar-thin min-h-0 flex-1 overflow-y-auto px-5 py-4">
        {!doc && !error && <Loader2 className="mx-auto mt-10 h-5 w-5 animate-spin text-muted" />}
        {doc && (
          <>
            {before && <Markdown>{render(before)}</Markdown>}
            {marked && (
              <div ref={markRef} className="-mx-2 my-1 rounded-lg bg-highlight px-2 py-1 ring-2 ring-[var(--warning)]/30">
                <Markdown>{render(marked)}</Markdown>
              </div>
            )}
            {after && <Markdown>{render(after)}</Markdown>}
          </>
        )}
      </div>
    </div>
  );
}
