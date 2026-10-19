// AX 관리자: 비용·토큰·지연·피드백 요약, 경로/모델/역할별 분해, 질의 로그, 파서 로그.
"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { Guard, PageHeader } from "@/components/Guard";
import { api } from "@/lib/api";
import { ROLE_LABEL, ROUTE_LABEL, type Role, type Route } from "@/lib/types";

interface Agg {
  queries: number;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd: number;
  p50_ms: number;
  p95_ms: number;
}
interface Ops {
  summary: Agg & { thumbs_down_rate: number | null; feedback_count: number };
  by_route: Record<string, Agg>;
  by_model: Record<string, Agg>;
  by_role: Record<string, Agg>;
  daily: (Agg & { date: string })[];
  logs: {
    created_at: string;
    role: Role | null;
    is_demo: boolean | null;
    question: string;
    route: Route | null;
    refused: boolean;
    model: string | null;
    prompt_tokens: number;
    completion_tokens: number;
    cost_usd: number;
    latency_ms: number;
    trace_id: string;
    feedback: number | null;
  }[];
  parse_jobs: {
    created_at: string;
    title: string;
    file_name: string;
    size_bytes: number;
    file_format: string;
    score: number | null;
    ocr_used: boolean;
    verdict: string;
    duration_ms: number;
    chunks: number;
  }[];
  pricing: { input_per_m: number; output_per_m: number };
}

const won = (usd: number) => `₩${Math.round(usd * 1400).toLocaleString()}`;
const usd = (v: number) => `$${v.toFixed(v < 0.01 ? 5 : 3)}`;

export default function OpsPage() {
  const [days, setDays] = useState(7);
  const [data, setData] = useState<Ops | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    api<Ops>(`/admin/ops?days=${days}`)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [days]);

  const s = data?.summary;
  const maxDaily = Math.max(1, ...(data?.daily || []).map((d) => d.queries));

  return (
    <Guard roles={["ax_admin"]}>
      <div className="scrollbar-thin h-full overflow-y-auto">
        <div className="mx-auto max-w-6xl px-4 py-6">
          <div className="flex flex-wrap items-end justify-between gap-2">
            <PageHeader title="비용·토큰·로그" desc="질의마다 경로·모델·토큰·비용·지연을 기록합니다. Gemini 무료 티어라 실제 청구는 0원이며, 비용은 유료 단가 기준 환산값이에요." />
            <div className="flex gap-1 rounded-lg bg-surface p-1 text-xs">
              {[1, 7, 30].map((d) => (
                <button key={d} onClick={() => setDays(d)} className={`rounded-md px-3 py-1 ${days === d ? "bg-bg font-semibold shadow-sm" : "text-muted"}`}>
                  {d === 1 ? "오늘" : `${d}일`}
                </button>
              ))}
            </div>
          </div>
          {error && <p className="mt-4 rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>}
          {!data && !error && <Loader2 className="mx-auto mt-16 h-6 w-6 animate-spin text-muted" />}
          {data && s && (
            <>
              <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
                <Card label="질의 수" value={s.queries.toLocaleString()} />
                <Card label="입력 토큰" value={s.prompt_tokens.toLocaleString()} />
                <Card label="출력 토큰" value={s.completion_tokens.toLocaleString()} />
                <Card label="환산 비용" value={usd(s.cost_usd)} sub={`${won(s.cost_usd)} · 질의당 ${s.queries ? usd(s.cost_usd / s.queries) : "-"}`} />
                <Card label="응답시간 p50 / p95" value={`${(s.p50_ms / 1000).toFixed(1)}s / ${(s.p95_ms / 1000).toFixed(1)}s`} sub="목표 p95 3초 (PRD)" />
                <Card label="👎 비율" value={s.thumbs_down_rate == null ? "-" : `${(s.thumbs_down_rate * 100).toFixed(1)}%`} sub={`피드백 ${s.feedback_count}건`} />
              </div>
              <p className="mt-2 text-[11px] text-muted">
                환산 단가: 입력 ${data.pricing.input_per_m}/1M · 출력 ${data.pricing.output_per_m}/1M 토큰 (환율 1,400원 가정)
              </p>

              <section className="mt-6 rounded-xl border border-line p-4">
                <h2 className="text-sm font-bold">일별 질의 수</h2>
                <div className="mt-3 flex h-32 items-end gap-1">
                  {data.daily.length === 0 && <p className="text-sm text-muted">기록이 없어요.</p>}
                  {data.daily.map((d) => (
                    <div key={d.date} className="group flex flex-1 flex-col items-center justify-end">
                      <span className="mb-1 text-[10px] text-muted opacity-0 group-hover:opacity-100">{d.queries}</span>
                      <div className="w-full max-w-10 rounded-t bg-brand" style={{ height: `${(d.queries / maxDaily) * 100}%` }} title={`${d.date}: ${d.queries}건 · ${usd(d.cost_usd)}`} />
                      <span className="mt-1 text-[10px] text-muted">{d.date.slice(5)}</span>
                    </div>
                  ))}
                </div>
              </section>

              <div className="mt-4 grid gap-4 lg:grid-cols-3">
                <Breakdown title="경로별" rows={data.by_route} label={(k) => ROUTE_LABEL[k as Route] || k} />
                <Breakdown title="모델별" rows={data.by_model} label={(k) => k} />
                <Breakdown title="역할별" rows={data.by_role} label={(k) => ROLE_LABEL[k as Role] || k} />
              </div>

              <section className="mt-6">
                <h2 className="mb-2 text-sm font-bold">질의 로그 (최근 100건, 질문은 마스킹 저장)</h2>
                <div className="overflow-x-auto rounded-xl border border-line">
                  <table className="w-full min-w-[960px] text-xs">
                    <thead className="bg-surface text-left text-muted">
                      <tr>
                        {["시간", "역할", "질문", "경로", "모델", "입력", "출력", "비용", "지연", "피드백", "트레이스"].map((h) => (
                          <th key={h} className="px-2.5 py-2 font-semibold">
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line">
                      {data.logs.map((l, i) => (
                        <tr key={i}>
                          <td className="whitespace-nowrap px-2.5 py-2 text-muted">{new Date(l.created_at).toLocaleString("ko-KR", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })}</td>
                          <td className="whitespace-nowrap px-2.5 py-2">
                            {l.role ? ROLE_LABEL[l.role] : "-"}
                            {l.is_demo ? " (데모)" : ""}
                          </td>
                          <td className="max-w-64 truncate px-2.5 py-2" title={l.question}>
                            {l.question}
                          </td>
                          <td className="whitespace-nowrap px-2.5 py-2">
                            {l.route ? ROUTE_LABEL[l.route] : "-"}
                            {l.refused && l.route === "rag" ? " · 근거없음" : ""}
                          </td>
                          <td className="whitespace-nowrap px-2.5 py-2 text-muted">{l.model?.replace("gemini/", "") || "-"}</td>
                          <td className="px-2.5 py-2 text-right">{l.prompt_tokens?.toLocaleString()}</td>
                          <td className="px-2.5 py-2 text-right">{l.completion_tokens?.toLocaleString()}</td>
                          <td className="px-2.5 py-2 text-right">{usd(l.cost_usd)}</td>
                          <td className="px-2.5 py-2 text-right">{(l.latency_ms / 1000).toFixed(1)}s</td>
                          <td className="px-2.5 py-2 text-center">{l.feedback === 1 ? "👍" : l.feedback === -1 ? "👎" : ""}</td>
                          <td className="px-2.5 py-2 font-mono text-[10px] text-muted">{l.trace_id?.slice(0, 8)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="mt-6">
                <h2 className="mb-2 text-sm font-bold">파서 로그 (자동 승인 판정)</h2>
                <div className="overflow-x-auto rounded-xl border border-line">
                  <table className="w-full min-w-[760px] text-xs">
                    <thead className="bg-surface text-left text-muted">
                      <tr>
                        {["시간", "파일", "형식", "크기", "인식률", "OCR", "판정", "청크", "처리"].map((h) => (
                          <th key={h} className="px-2.5 py-2 font-semibold">
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line">
                      {data.parse_jobs.map((j, i) => (
                        <tr key={i}>
                          <td className="whitespace-nowrap px-2.5 py-2 text-muted">{new Date(j.created_at).toLocaleString("ko-KR", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })}</td>
                          <td className="max-w-56 truncate px-2.5 py-2" title={j.title}>
                            {j.file_name || j.title}
                          </td>
                          <td className="px-2.5 py-2 uppercase">{j.file_format}</td>
                          <td className="px-2.5 py-2">{j.size_bytes ? `${(j.size_bytes / 1024).toFixed(0)}KB` : "-"}</td>
                          <td className="px-2.5 py-2">{j.score != null ? `${(j.score * 100).toFixed(1)}%` : "-"}</td>
                          <td className="px-2.5 py-2">{j.ocr_used ? "사용" : ""}</td>
                          <td className="px-2.5 py-2 font-semibold">{{ approved: "승인", held: "보류", rejected: "반려" }[j.verdict] || j.verdict}</td>
                          <td className="px-2.5 py-2">{j.chunks ?? "-"}</td>
                          <td className="px-2.5 py-2">{j.duration_ms ? `${(j.duration_ms / 1000).toFixed(1)}s` : "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </>
          )}
        </div>
      </div>
    </Guard>
  );
}

function Card({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-line p-3">
      <p className="text-[11px] text-muted">{label}</p>
      <p className="mt-1 text-lg font-bold">{value}</p>
      {sub && <p className="text-[11px] text-muted">{sub}</p>}
    </div>
  );
}

function Breakdown({ title, rows, label }: { title: string; rows: Record<string, Agg>; label: (k: string) => string }) {
  const entries = Object.entries(rows).sort((a, b) => b[1].queries - a[1].queries);
  const max = Math.max(1, ...entries.map(([, v]) => v.queries));
  return (
    <section className="rounded-xl border border-line p-4">
      <h2 className="text-sm font-bold">{title}</h2>
      <div className="mt-3 space-y-2">
        {entries.length === 0 && <p className="text-sm text-muted">-</p>}
        {entries.map(([k, v]) => (
          <div key={k} className="text-xs">
            <div className="flex justify-between">
              <span>{label(k)}</span>
              <span className="text-muted">
                {v.queries}건 · {usd(v.cost_usd)} · p95 {(v.p95_ms / 1000).toFixed(1)}s
              </span>
            </div>
            <div className="mt-1 h-1.5 rounded-full bg-surface">
              <div className="h-full rounded-full bg-action" style={{ width: `${(v.queries / max) * 100}%` }} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
