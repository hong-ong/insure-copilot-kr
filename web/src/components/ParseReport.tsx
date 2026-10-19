// 파싱 리포트: 한글 인식률 게이지와 자동 판정(승인·보류·반려), 문제 목록.
"use client";

import { CheckCircle2, CircleAlert, CircleX, Loader2 } from "lucide-react";

export interface ParseJob {
  file_format: string;
  score: number | null;
  ocr_used: boolean;
  verdict: "approved" | "held" | "rejected" | null;
  issues: string[];
  pages: number | null;
  chars: number | null;
  chunks: number | null;
  duration_ms: number | null;
}

const VERDICT = {
  approved: { label: "자동 승인", desc: "한글 인식률 90% 이상 → 검색에 반영했어요.", icon: CheckCircle2, cls: "text-success bg-accent-soft" },
  held: { label: "보류", desc: "인식률 70~90% → 미리보기를 확인하고 등록할지 정해 주세요.", icon: CircleAlert, cls: "text-warning bg-warning-soft" },
  rejected: { label: "반려", desc: "인식률 70% 미만이거나 열 수 없는 파일이에요.", icon: CircleX, cls: "text-danger bg-danger-soft" },
} as const;

export function ParseReport({ job, status }: { job: ParseJob | null; status: string }) {
  if (!job) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-line px-4 py-3 text-sm text-muted">
        <Loader2 className="h-4 w-4 animate-spin" />
        {status === "parsing" ? "파싱 → 한글 인식률 검사 → 조항 분할 → 임베딩 중…" : "처리 기록을 불러오는 중…"}
      </div>
    );
  }
  const v = VERDICT[job.verdict || "rejected"];
  const pct = job.score != null ? Math.round(job.score * 1000) / 10 : null;
  return (
    <div className="rounded-xl border border-line p-4">
      <div className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold ${v.cls}`}>
        <v.icon className="h-3.5 w-3.5" /> {v.label}
      </div>
      <p className="mt-1.5 text-sm text-muted">{v.desc}</p>

      {pct != null && (
        <div className="mt-4">
          <div className="flex items-end justify-between text-xs">
            <span className="font-semibold">한글 인식률</span>
            <span className="text-lg font-bold">{pct}%</span>
          </div>
          <div className="relative mt-1.5 h-2.5 rounded-full bg-surface">
            <div
              className={`h-full rounded-full ${pct >= 90 ? "bg-accent" : pct >= 70 ? "bg-warning" : "bg-danger"}`}
              style={{ width: `${Math.min(100, pct)}%` }}
            />
            <span className="absolute top-[-3px] h-4 w-px bg-text/50" style={{ left: "70%" }} />
            <span className="absolute top-[-3px] h-4 w-px bg-text/50" style={{ left: "90%" }} />
          </div>
          <div className="relative mt-1 h-4 text-[10px] text-muted">
            <span className="absolute -translate-x-1/2" style={{ left: "70%" }}>
              보류 70
            </span>
            <span className="absolute -translate-x-1/2" style={{ left: "90%" }}>
              승인 90
            </span>
          </div>
        </div>
      )}

      <dl className="mt-3 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
        <Stat k="형식" v={job.file_format.toUpperCase()} />
        <Stat k="페이지" v={job.pages ?? "-"} />
        <Stat k="조항·구간 청크" v={job.chunks ?? "-"} />
        <Stat k="처리 시간" v={job.duration_ms != null ? `${(job.duration_ms / 1000).toFixed(1)}초` : "-"} />
      </dl>
      {job.ocr_used && <p className="mt-2 text-xs text-action">원문 추출이 깨져서 OCR(이미지 인식)로 다시 읽었어요.</p>}
      {job.issues?.length > 0 && (
        <ul className="mt-3 space-y-1 rounded-lg bg-surface p-3 text-xs text-muted">
          {job.issues.map((i) => (
            <li key={i}>· {i}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Stat({ k, v }: { k: string; v: string | number }) {
  return (
    <div className="rounded-lg bg-surface px-2.5 py-2">
      <dt className="text-muted">{k}</dt>
      <dd className="mt-0.5 font-semibold">{v}</dd>
    </div>
  );
}
