// AX 관리자: 평가 대시보드 — 골든셋 실행 결과와 실험 전후 비교. 숫자는 실제로 실행한 값만 보여 준다.
"use client";

import { useEffect, useState } from "react";
import { FlaskConical, Loader2 } from "lucide-react";
import { Guard, PageHeader } from "@/components/Guard";
import { supabaseBrowser } from "@/lib/supabase/client";

interface Run {
  id: string;
  name: string;
  config: Record<string, unknown>;
  metrics: Record<string, number>;
  notes: string | null;
  created_at: string;
}

const METRICS = [
  { key: "recall_at_5", label: "Recall@5", desc: "정답 근거 조문이 검색 상위 5개 안에 든 비율", fmt: "pct", goal: "검색" },
  { key: "mrr", label: "MRR", desc: "정답 조문이 몇 번째에 나왔는지의 역수 평균 (1이면 항상 1등)", fmt: "num", goal: "검색" },
  { key: "faithfulness", label: "Faithfulness", desc: "답변 문장이 근거에 실제로 있는 내용인지 (근거 충실도)", fmt: "pct", goal: "생성" },
  { key: "refusal_accuracy", label: "거절 정확도", desc: "거절해야 할 때 거절하고, 답해야 할 때 답한 비율", fmt: "pct", goal: "가드레일" },
  { key: "routing_accuracy", label: "라우팅 정확도", desc: "질문을 약관/지표/거절로 올바르게 보낸 비율", fmt: "pct", goal: "라우터" },
  { key: "p95_ms", label: "p95 응답시간", desc: "느린 쪽 5%를 뺀 최대 응답 시간 (목표 3초)", fmt: "ms", goal: "운영" },
  { key: "cost_per_query", label: "질의당 비용", desc: "유료 단가 기준 환산 비용", fmt: "usd", goal: "운영" },
];

function fmt(v: number | undefined, kind: string) {
  if (v == null) return "—";
  if (kind === "pct") return `${(v * 100).toFixed(1)}%`;
  if (kind === "ms") return `${(v / 1000).toFixed(2)}s`;
  if (kind === "usd") return `$${v.toFixed(5)}`;
  return v.toFixed(3);
}

export default function EvalPage() {
  const supabase = supabaseBrowser();
  const [runs, setRuns] = useState<Run[] | null>(null);

  useEffect(() => {
    supabase
      .from("eval_runs")
      .select("*")
      .order("created_at", { ascending: true })
      .then(({ data }) => setRuns((data as Run[]) || []));
  }, [supabase]);

  const baseline = runs?.[0];
  const latest = runs && runs.length > 0 ? runs[runs.length - 1] : undefined;

  return (
    <Guard roles={["ax_admin"]}>
      <div className="scrollbar-thin h-full overflow-y-auto">
        <div className="mx-auto max-w-5xl px-4 py-6">
          <PageHeader
            title="평가 대시보드"
            desc="골든셋(정답이 정해진 질문 묶음)으로 검색·생성·거절·라우팅 품질을 숫자로 잽니다. 실험(E1~E6)마다 한 번에 변수 하나만 바꿔 전후를 비교합니다."
          />
          {runs === null && <Loader2 className="mx-auto mt-16 h-6 w-6 animate-spin text-muted" />}

          {runs && (
            <>
              <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-4">
                {METRICS.map((m) => {
                  const b = baseline?.metrics[m.key];
                  const l = latest?.metrics[m.key];
                  const delta = b != null && l != null && runs.length > 1 ? l - b : null;
                  return (
                    <div key={m.key} className="rounded-xl border border-line p-3" title={m.desc}>
                      <p className="text-[11px] text-muted">
                        {m.goal} · {m.label}
                      </p>
                      <p className="mt-1 text-xl font-bold">{fmt(l, m.fmt)}</p>
                      <p className="text-[11px] text-muted">
                        베이스라인 {fmt(b, m.fmt)}
                        {delta != null && (
                          <span className={delta >= 0 === !["p95_ms", "cost_per_query"].includes(m.key) ? " text-success" : " text-danger"}>
                            {" "}
                            ({delta >= 0 ? "+" : ""}
                            {m.fmt === "pct" ? `${(delta * 100).toFixed(1)}%p` : fmt(Math.abs(delta), m.fmt)})
                          </span>
                        )}
                      </p>
                    </div>
                  );
                })}
              </div>

              {runs.length === 0 ? (
                <div className="mt-6 rounded-2xl border border-dashed border-line p-6">
                  <div className="flex items-start gap-3">
                    <FlaskConical className="mt-0.5 h-5 w-5 text-brand" />
                    <div className="text-sm">
                      <p className="font-semibold">아직 평가 실행 기록이 없어요</p>
                      <p className="mt-1 text-muted">
                        골든셋(약관·규정 50 + 지표 20 + 권한 10 문항)은 3주차에 직접 작성합니다. 정답과 근거 조문은 AI가 아니라 약관을 직접 확인해 채웁니다.
                        작성 후 평가 스크립트를 실행하면 여기에 베이스라인과 실험 결과가 쌓입니다. 숫자는 실제로 실행한 값만 표시합니다.
                      </p>
                      <ol className="mt-3 list-decimal space-y-1 pl-5 text-muted">
                        <li>
                          <code>eval/golden/golden_v1.csv</code> 작성 (질문·기대 답·근거 조문 ID·유형·거절 여부·라우팅 정답)
                        </li>
                        <li>베이스라인 실행 → 실패 사례를 읽고 실패 유형표 작성 (4주차)</li>
                        <li>실험 E1~E6: 청킹·임베딩·검색 방식·용어 사전·리랭커·생성 검증 (5주차)</li>
                      </ol>
                    </div>
                  </div>
                </div>
              ) : (
                <section className="mt-6">
                  <h2 className="mb-2 text-sm font-bold">실행 이력</h2>
                  <div className="overflow-x-auto rounded-xl border border-line">
                    <table className="w-full min-w-[800px] text-xs">
                      <thead className="bg-surface text-left text-muted">
                        <tr>
                          <th className="px-2.5 py-2">실행</th>
                          {METRICS.map((m) => (
                            <th key={m.key} className="px-2.5 py-2">
                              {m.label}
                            </th>
                          ))}
                          <th className="px-2.5 py-2">메모</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-line">
                        {runs.map((r) => (
                          <tr key={r.id}>
                            <td className="px-2.5 py-2">
                              <p className="font-semibold">{r.name}</p>
                              <p className="text-muted">{new Date(r.created_at).toLocaleDateString("ko-KR")}</p>
                            </td>
                            {METRICS.map((m) => (
                              <td key={m.key} className="px-2.5 py-2">
                                {fmt(r.metrics[m.key], m.fmt)}
                              </td>
                            ))}
                            <td className="max-w-56 px-2.5 py-2 text-muted">{r.notes}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              )}

              <section className="mt-6 rounded-xl border border-line p-4">
                <h2 className="text-sm font-bold">지표 정의</h2>
                <dl className="mt-2 grid gap-2 text-xs sm:grid-cols-2">
                  {METRICS.map((m) => (
                    <div key={m.key}>
                      <dt className="font-semibold">{m.label}</dt>
                      <dd className="text-muted">{m.desc}</dd>
                    </div>
                  ))}
                </dl>
              </section>
            </>
          )}
        </div>
      </div>
    </Guard>
  );
}
