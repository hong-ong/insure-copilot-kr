// 파일 업로드(데이터 넣기): 공개 범위(전체/팀), 새 판(개정안) 연결, 자동 파싱 판정, 내 업로드 목록.
"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { FileDiff, FileUp, Loader2, Lock } from "lucide-react";
import { useApp } from "@/components/app/AppContext";
import { ParseReport, type ParseJob } from "@/components/ParseReport";
import { api } from "@/lib/api";
import { supabaseBrowser } from "@/lib/supabase/client";
import { DOC_TYPE_LABEL, TEAM_LABEL } from "@/lib/types";

const MAX = 10 * 1024 * 1024;

interface DocRow {
  id: string;
  title: string;
  doc_type: string;
  version_label: string | null;
  version_group_id: string;
  status: string;
  visibility: string;
  owner_team: string;
  created_at: string;
  file_name: string | null;
  parse_jobs: ParseJob[];
}

const STATUS: Record<string, string> = {
  parsing: "처리 중",
  held: "보류",
  rejected: "반려",
  active: "검색 반영",
  expired: "구버전",
};

export default function UploadPage() {
  const { profile } = useApp();
  const supabase = supabaseBrowser();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [docType, setDocType] = useState("internal");
  const [product, setProduct] = useState("");
  const [visibility, setVisibility] = useState<"all" | "team">("team");
  const [groupId, setGroupId] = useState("");
  const [versionLabel, setVersionLabel] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [current, setCurrent] = useState<string | null>(null);
  const [mine, setMine] = useState<DocRow[]>([]);
  const [groups, setGroups] = useState<{ version_group_id: string; title: string; version_label: string | null }[]>([]);
  const [sample, setSample] = useState<DocRow | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!profile) return;
    supabase
      .from("documents")
      .select("version_group_id, title, version_label")
      .eq("status", "active")
      .in("doc_type", ["terms", "law", "internal"])
      .order("title")
      .then(({ data }) => setGroups(data || []));
    if (profile.is_demo) {
      // 데모: 시스템이 올린 개정안(2026.04 판)의 실제 처리 결과를 보여 준다
      supabase
        .from("documents")
        .select("*, parse_jobs(*)")
        .eq("doc_type", "terms")
        .eq("status", "active")
        .order("created_at", { ascending: false })
        .limit(1)
        .then(({ data }) => setSample((data?.[0] as DocRow) || null));
    } else {
      supabase
        .from("documents")
        .select("*, parse_jobs(*)")
        .eq("uploaded_by", profile.id)
        .order("created_at", { ascending: false })
        .limit(30)
        .then(({ data }) => setMine((data as DocRow[]) || []));
    }
  }, [profile, supabase, tick]);

  // 처리 중인 문서가 있으면 2초마다 상태를 다시 읽는다
  useEffect(() => {
    if (!mine.some((d) => d.status === "parsing" || (d.parse_jobs.length === 0 && d.status !== "active"))) return;
    const t = setTimeout(() => setTick((x) => x + 1), 2000);
    return () => clearTimeout(t);
  }, [mine]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    if (file.size > MAX) {
      setError("파일은 10MB 이하만 올릴 수 있어요. (파싱·OCR 비용 때문에 제한합니다)");
      return;
    }
    setBusy(true);
    setError(null);
    const form = new FormData();
    form.append("file", file);
    form.append("title", title || file.name.replace(/\.[^.]+$/, ""));
    form.append("doc_type", docType);
    if (product) form.append("product", product);
    form.append("visibility", visibility);
    if (groupId) form.append("version_group_id", groupId);
    if (versionLabel) form.append("version_label", versionLabel);
    if (effectiveFrom) form.append("effective_from", effectiveFrom);
    try {
      const r = await api<{ document_id: string }>("/documents", { method: "POST", body: form });
      setCurrent(r.document_id);
      setFile(null);
      setTitle("");
      setTick((x) => x + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "업로드 실패");
    } finally {
      setBusy(false);
    }
  }

  async function activate(id: string) {
    await api(`/documents/${id}/activate`, { method: "POST" });
    setTick((x) => x + 1);
  }
  async function cancel(id: string) {
    if (!confirm("이 업로드를 취소할까요?")) return;
    await api(`/documents/${id}`, { method: "DELETE" });
    if (current === id) setCurrent(null);
    setTick((x) => x + 1);
  }

  const currentDoc = mine.find((d) => d.id === current);

  return (
    <div className="scrollbar-thin h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-4 py-6">
        <h1 className="text-xl font-bold">파일 업로드</h1>
        <p className="mt-1 text-sm text-muted">
          약관 개정안·사내 문서를 올리면 파서가 자동으로 읽고, <b>한글 인식률 90% 이상이면 자동 승인</b>되어 검색에 반영됩니다.
          PDF·HWP·HWPX·DOCX·TXT·MD, 10MB 이하.
        </p>

        {profile?.is_demo ? (
          <div className="mt-6 space-y-4">
            <div className="flex items-start gap-3 rounded-xl border border-line bg-surface p-4 text-sm">
              <Lock className="mt-0.5 h-4 w-4 shrink-0 text-muted" />
              <div>
                데모 계정은 파일을 올릴 수 없어요. 대신 미리 올려 둔 <b>개정안 샘플</b>의 실제 처리 결과를 보여 드릴게요.
                <br />
                가입하면 직접 파일을 올려 볼 수 있습니다.
              </div>
            </div>
            {sample && (
              <div className="rounded-xl border border-line p-4">
                <p className="text-xs text-muted">샘플 업로드</p>
                <p className="font-semibold">
                  {sample.title} · {sample.version_label}
                </p>
                <div className="mt-3">
                  <ParseReport job={sample.parse_jobs[0] || null} status={sample.status} />
                </div>
                <Link
                  href={`/documents/${sample.id}/diff`}
                  className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-brand px-3 py-2 text-sm font-semibold text-white"
                >
                  <FileDiff className="h-4 w-4" /> 자동 생성된 신구대비표 보기
                </Link>
              </div>
            )}
          </div>
        ) : (
          <>
            <form onSubmit={submit} className="mt-6 space-y-4 rounded-2xl border border-line p-5">
              <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-line px-4 py-8 text-sm hover:border-brand">
                <FileUp className="h-6 w-6 text-muted" />
                {file ? (
                  <span className="font-semibold">
                    {file.name} <span className="font-normal text-muted">({(file.size / 1024 / 1024).toFixed(2)}MB)</span>
                  </span>
                ) : (
                  <span className="text-muted">눌러서 파일 선택</span>
                )}
                <input
                  type="file"
                  accept=".pdf,.hwp,.hwpx,.docx,.txt,.md"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0] || null;
                    setFile(f);
                    if (f && !title) setTitle(f.name.replace(/\.[^.]+$/, ""));
                    setError(f && f.size > MAX ? "파일은 10MB 이하만 올릴 수 있어요." : null);
                  }}
                />
              </label>

              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="제목">
                  <input value={title} onChange={(e) => setTitle(e.target.value)} required className={inputCls} />
                </Field>
                <Field label="문서 종류">
                  <select value={docType} onChange={(e) => setDocType(e.target.value)} className={inputCls}>
                    {["terms", "law", "case", "internal"].map((t) => (
                      <option key={t} value={t}>
                        {DOC_TYPE_LABEL[t]}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="상품·담보 (선택)">
                  <input value={product} onChange={(e) => setProduct(e.target.value)} placeholder="예: 실손의료비" className={inputCls} />
                </Field>
                <Field label="공개 범위">
                  <div className="flex gap-2">
                    {(["all", "team"] as const).map((v) => (
                      <button
                        type="button"
                        key={v}
                        onClick={() => setVisibility(v)}
                        className={`h-10 flex-1 rounded-lg border text-sm ${
                          visibility === v ? "border-brand bg-brand-soft font-semibold text-brand" : "border-line"
                        }`}
                      >
                        {v === "all" ? "전체 공개" : `${profile ? TEAM_LABEL[profile.team] : "팀"}만`}
                      </button>
                    ))}
                  </div>
                </Field>
              </div>

              <div className="rounded-xl bg-surface p-3">
                <p className="text-xs font-semibold">개정안인가요? (선택)</p>
                <p className="text-xs text-muted">기존 문서의 새 판으로 올리면 이전 판은 구버전으로 보존되고, 신구대비표가 자동으로 만들어져요.</p>
                <div className="mt-2 grid gap-2 sm:grid-cols-3">
                  <select value={groupId} onChange={(e) => setGroupId(e.target.value)} className={`${inputCls} sm:col-span-3`}>
                    <option value="">새 문서로 등록</option>
                    {groups.map((g) => (
                      <option key={g.version_group_id} value={g.version_group_id}>
                        {g.title} {g.version_label ? `(현재 ${g.version_label})` : ""}의 새 판
                      </option>
                    ))}
                  </select>
                  <input value={versionLabel} onChange={(e) => setVersionLabel(e.target.value)} placeholder="판 이름 (예: 2026.10 판)" className={inputCls} />
                  <input type="date" value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} className={inputCls} />
                  <span className="self-center text-[11px] text-muted">← 적용 시작일</span>
                </div>
              </div>

              {error && <p className="rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>}
              <button
                disabled={!file || busy || (file?.size || 0) > MAX}
                className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-brand text-sm font-semibold text-white disabled:opacity-40"
              >
                {busy && <Loader2 className="h-4 w-4 animate-spin" />} 올리고 자동 검사하기
              </button>
            </form>

            {currentDoc && (
              <section className="mt-6">
                <h2 className="mb-2 text-sm font-bold">방금 올린 파일 · {currentDoc.title}</h2>
                <ParseReport job={currentDoc.parse_jobs[0] || null} status={currentDoc.status} />
                <DocActions d={currentDoc} onActivate={activate} onCancel={cancel} />
              </section>
            )}

            <section className="mt-8">
              <h2 className="mb-2 text-sm font-bold">내 업로드</h2>
              {mine.length === 0 && <p className="text-sm text-muted">아직 올린 파일이 없어요.</p>}
              <div className="divide-y divide-line rounded-xl border border-line">
                {mine.map((d) => {
                  const job = d.parse_jobs[0];
                  return (
                    <div key={d.id} className="flex flex-wrap items-center gap-2 px-4 py-3 text-sm">
                      <div className="min-w-0 flex-1">
                        <Link href={`/documents/${d.id}`} className="font-semibold hover:underline">
                          {d.title}
                        </Link>
                        <p className="text-xs text-muted">
                          {DOC_TYPE_LABEL[d.doc_type]} · {d.visibility === "all" ? "전체 공개" : `${TEAM_LABEL[d.owner_team as keyof typeof TEAM_LABEL]}만`}
                          {d.version_label ? ` · ${d.version_label}` : ""} · {new Date(d.created_at).toLocaleString("ko-KR")}
                        </p>
                      </div>
                      {job?.score != null && <span className="text-xs text-muted">인식률 {(job.score * 100).toFixed(1)}%</span>}
                      <span className="rounded-full bg-surface px-2 py-0.5 text-xs font-semibold">{STATUS[d.status] || d.status}</span>
                      {d.status === "held" && (
                        <button onClick={() => setCurrent(d.id)} className="text-xs text-action">
                          확인하기
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  );
}

function DocActions({ d, onActivate, onCancel }: { d: DocRow; onActivate: (id: string) => void; onCancel: (id: string) => void }) {
  if (d.status === "held") {
    return (
      <div className="mt-3 rounded-xl border border-line p-4">
        <p className="text-sm font-semibold">파싱 미리보기를 확인해 주세요</p>
        <p className="text-xs text-muted">글자가 일부 깨졌을 수 있어요. 검색 품질이 떨어질 수 있지만 그래도 등록할 수 있습니다.</p>
        <div className="mt-2 flex gap-2">
          <Link href={`/documents/${d.id}`} target="_blank" className="rounded-lg border border-line px-3 py-1.5 text-sm hover:bg-surface">
            미리보기
          </Link>
          <button onClick={() => onActivate(d.id)} className="rounded-lg bg-brand px-3 py-1.5 text-sm font-semibold text-white">
            그래도 등록
          </button>
          <button onClick={() => onCancel(d.id)} className="rounded-lg px-3 py-1.5 text-sm text-danger hover:bg-danger-soft">
            취소
          </button>
        </div>
      </div>
    );
  }
  if (d.status === "rejected") {
    return (
      <button onClick={() => onCancel(d.id)} className="mt-3 rounded-lg px-3 py-1.5 text-sm text-danger hover:bg-danger-soft">
        반려된 파일 지우기
      </button>
    );
  }
  if (d.status === "active") {
    return (
      <div className="mt-3 flex gap-2">
        <Link href={`/documents/${d.id}`} className="rounded-lg border border-line px-3 py-1.5 text-sm hover:bg-surface">
          원문 보기
        </Link>
        <Link href={`/documents/${d.id}/diff`} className="rounded-lg border border-line px-3 py-1.5 text-sm hover:bg-surface">
          신구대비표 (개정안인 경우)
        </Link>
        <Link href="/chat" className="rounded-lg bg-brand px-3 py-1.5 text-sm font-semibold text-white">
          검색에서 써 보기
        </Link>
      </div>
    );
  }
  return null;
}

const inputCls = "h-10 w-full rounded-lg border border-line bg-bg px-3 text-sm outline-none focus:border-action";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-semibold">{label}</span>
      {children}
    </label>
  );
}
