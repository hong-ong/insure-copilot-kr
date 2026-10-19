// 답변 카드: 경로 배지 · 본문 · 출처 칩(클릭 → 원문) · 버전 배지 · AI 생성 라벨 · 피드백 · 법무팀 문의.
"use client";

import { useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  BookOpenText,
  Check,
  Code2,
  Loader2,
  Scale,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";
import { Markdown } from "@/components/Markdown";
import { useApp } from "@/components/app/AppContext";
import { api } from "@/lib/api";
import { supabaseBrowser } from "@/lib/supabase/client";
import { ROUTE_LABEL, type ChatMessage, type Citation } from "@/lib/types";

const REASONS = ["답이 틀림", "출처가 틀림", "약관 버전이 틀림", "거절하지 말았어야 함", "거절했어야 함", "기타"];

const ROUTE_STYLE: Record<string, string> = {
  rag: "bg-brand-soft text-brand",
  genbi: "bg-accent-soft text-success",
  refuse: "bg-danger-soft text-danger",
  out_of_scope: "bg-surface text-muted",
};

export function MessageCard({ m, initialRating }: { m: ChatMessage; initialRating?: number | null }) {
  const { openViewer, profile } = useApp();
  const [rating, setRating] = useState<number | null>(initialRating ?? null);
  const [askReason, setAskReason] = useState(false);
  const [reasons, setReasons] = useState<string[]>([]);
  const [comment, setComment] = useState("");
  const [inquiry, setInquiry] = useState<"idle" | "busy" | "done">("idle");
  const [showSql, setShowSql] = useState(false);
  const supabase = supabaseBrowser();

  if (m.pending) {
    return (
      <div className="flex items-center gap-2 py-3 text-sm text-muted">
        <Loader2 className="h-4 w-4 animate-spin" /> 근거 조항을 찾고 답변을 만드는 중…
      </div>
    );
  }
  if (m.error) {
    return <div className="rounded-xl bg-danger-soft px-4 py-3 text-sm text-danger">{m.content}</div>;
  }

  const cites = m.citations || [];
  const meta = (m.meta || {}) as Record<string, unknown>;
  const route = m.route || "rag";
  const versions = Array.from(new Set(cites.filter((c) => !c.is_expired && c.version_label).map((c) => c.version_label)));
  const hasExpired = cites.some((c) => c.is_expired);

  async function rate(value: 1 | -1, extra?: { reasons: string[]; comment: string }) {
    if (!profile) return;
    setRating(value);
    await supabase.from("feedback").upsert(
      {
        message_id: m.id,
        user_id: profile.id,
        rating: value,
        reasons: extra?.reasons || [],
        comment: extra?.comment || null,
      },
      { onConflict: "message_id,user_id" },
    );
  }

  async function sendInquiry() {
    setInquiry("busy");
    try {
      await api("/inquiries", { method: "POST", json: { message_id: m.id } });
      setInquiry("done");
    } catch (e) {
      alert(e instanceof Error ? e.message : "문의 접수 실패");
      setInquiry("idle");
    }
  }

  const open = (c: Citation) => openViewer(c);

  return (
    <div className="group">
      <div className="mb-2 flex flex-wrap items-center gap-1.5 text-[11px] font-semibold">
        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 ${ROUTE_STYLE[route]}`}>
          {route === "genbi" ? (
            <BarChart3 className="h-3 w-3" />
          ) : route === "refuse" ? (
            <Scale className="h-3 w-3" />
          ) : (
            <BookOpenText className="h-3 w-3" />
          )}
          {ROUTE_LABEL[route]}
        </span>
        {versions.map((v) => (
          <span key={v} className="rounded-full bg-surface px-2 py-0.5 text-muted">
            {v} 기준
          </span>
        ))}
        {hasExpired && <span className="rounded-full bg-warning-soft px-2 py-0.5 text-warning">구버전 비교 포함</span>}
        <span className="inline-flex items-center gap-1 rounded-full bg-surface px-2 py-0.5 text-muted">
          <Sparkles className="h-3 w-3" /> AI 생성
        </span>
      </div>

      <Markdown onCite={(rank) => cites[rank - 1] && open(cites[rank - 1])}>{m.content}</Markdown>

      {route === "genbi" && typeof meta.definition === "string" && (
        <div className="mt-3 rounded-lg border border-line bg-surface px-3 py-2 text-xs text-muted">
          <p>
            <b className="text-text">지표 정의</b> · {meta.definition as string}
          </p>
          <p className="mt-1">
            소유 부서 {String(meta.owner || "-")} · 조회 범위 {String(meta.scope)} · 가상 데이터 기준
          </p>
          {typeof meta.sql === "string" && (
            <>
              <button onClick={() => setShowSql((v) => !v)} className="mt-1.5 inline-flex items-center gap-1 text-action">
                <Code2 className="h-3 w-3" /> 계산에 쓴 SQL {showSql ? "닫기" : "보기"}
              </button>
              {showSql && (
                <pre className="mt-1.5 max-h-60 overflow-auto rounded bg-bg p-2 text-[11px] leading-snug text-text">{meta.sql as string}</pre>
              )}
            </>
          )}
        </div>
      )}

      {cites.length > 0 && (
        <div className="mt-3">
          <p className="mb-1.5 text-[11px] font-semibold text-muted">{route === "refuse" ? "참고할 관련 조문" : "출처"}</p>
          <div className="flex flex-col gap-1.5">
            {cites.map((c) => (
              <button
                key={`${c.chunk_id}-${c.rank}`}
                onClick={() => open(c)}
                title={c.snippet}
                className="flex items-start gap-2 rounded-lg border border-line px-3 py-2 text-left text-xs hover:border-brand hover:bg-brand-soft"
              >
                <span className="mt-px flex h-4 min-w-4 items-center justify-center rounded-full bg-brand-soft px-1 text-[10px] font-bold text-brand">
                  {c.rank}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="font-semibold">{c.label}</span>
                  {c.is_expired && <span className="ml-1.5 rounded bg-warning-soft px-1 py-px text-[10px] font-semibold text-warning">구버전</span>}
                  {c.snippet && <span className="mt-0.5 line-clamp-1 block text-muted">{c.snippet}</span>}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {route === "refuse" && (
        <div className="mt-3">
          {inquiry === "done" ? (
            <p className="inline-flex items-center gap-1.5 rounded-lg bg-accent-soft px-3 py-2 text-xs font-semibold text-success">
              <Check className="h-3.5 w-3.5" /> 법무팀에 문의를 보냈어요. 답변이 오면 알림으로 알려 드릴게요.
            </p>
          ) : (
            <button
              onClick={sendInquiry}
              disabled={inquiry === "busy" || profile?.is_demo}
              title={profile?.is_demo ? "데모 계정은 문의를 보낼 수 없어요" : undefined}
              className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-3 py-2 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-50"
            >
              {inquiry === "busy" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Scale className="h-3.5 w-3.5" />}
              법무팀에 문의
            </button>
          )}
        </div>
      )}

      {/* 피드백 */}
      <div className="mt-3 flex items-center gap-1 text-muted">
        <button
          onClick={() => rate(1)}
          className={`rounded-md p-1.5 hover:bg-surface ${rating === 1 ? "text-success" : ""}`}
          aria-label="좋아요"
        >
          <ThumbsUp className="h-4 w-4" />
        </button>
        <button
          onClick={() => setAskReason((v) => !v)}
          className={`rounded-md p-1.5 hover:bg-surface ${rating === -1 ? "text-danger" : ""}`}
          aria-label="별로예요"
        >
          <ThumbsDown className="h-4 w-4" />
        </button>
        {rating !== null && !askReason && <span className="text-[11px]">피드백 고마워요</span>}
      </div>
      {askReason && (
        <div className="mt-1 rounded-xl border border-line p-3">
          <p className="mb-2 text-xs font-semibold">무엇이 문제였나요? (여러 개 선택)</p>
          <div className="flex flex-wrap gap-1.5">
            {REASONS.map((r) => {
              const on = reasons.includes(r);
              return (
                <button
                  key={r}
                  onClick={() => setReasons(on ? reasons.filter((x) => x !== r) : [...reasons, r])}
                  className={`rounded-full border px-2.5 py-1 text-xs ${on ? "border-danger bg-danger-soft text-danger" : "border-line hover:bg-surface"}`}
                >
                  {r}
                </button>
              );
            })}
          </div>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="자세히 알려주시면 법무팀이 검토해 정답을 기록합니다 (선택)"
            className="mt-2 h-16 w-full resize-none rounded-lg border border-line bg-bg p-2 text-xs outline-none focus:border-action"
          />
          <div className="mt-2 flex justify-end gap-2">
            <button onClick={() => setAskReason(false)} className="rounded-lg px-3 py-1.5 text-xs hover:bg-surface">
              취소
            </button>
            <button
              onClick={async () => {
                await rate(-1, { reasons, comment });
                setAskReason(false);
              }}
              disabled={reasons.length === 0}
              className="rounded-lg bg-brand px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40"
            >
              보내기
            </button>
          </div>
        </div>
      )}

      {route === "rag" && !m.refused && (
        <p className="mt-2 flex items-center gap-1 text-[11px] text-muted">
          <AlertTriangle className="h-3 w-3" /> 고객 안내 전 출처 원문을 확인하세요.
        </p>
      )}
    </div>
  );
}
