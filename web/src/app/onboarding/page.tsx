// 가입 직후: 이름과 소속 팀 선택 (영업팀 = 설계사, 그 외 = 팀원). 법무·AX 관리자는 관리자가 부여한다.
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Footer, Wordmark } from "@/components/Brand";
import { api } from "@/lib/api";
import type { Profile } from "@/lib/types";

const TEAMS = [
  { id: "sales", label: "영업 (설계사)", desc: "약관 확인, 내 실적 지표" },
  { id: "underwriting", label: "심사", desc: "인수 심사 기준" },
  { id: "claims", label: "지급", desc: "보험금 청구·지급 기준" },
  { id: "education", label: "교육", desc: "보수교육 운영·이수율" },
  { id: "cs", label: "고객센터", desc: "보장 범위 문의 응대" },
];

export default function Onboarding() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [team, setTeam] = useState("sales");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<{ profile: Profile }>("/me")
      .then(({ profile }) => {
        if (profile.is_demo || profile.onboarded) router.replace("/chat");
        else setName(profile.display_name || "");
      })
      .catch((e) => setError(e.message));
  }, [router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api("/onboarding", { method: "POST", json: { team, display_name: name } });
      router.replace("/chat");
    } catch (err) {
      setError(err instanceof Error ? err.message : "저장 실패");
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-full flex-col">
      <main className="flex flex-1 items-center justify-center px-4 py-10">
        <form onSubmit={submit} className="w-full max-w-md rounded-2xl border border-line p-6">
          <Wordmark href="/onboarding" />
          <h1 className="mt-4 text-lg font-bold">가입을 환영해요</h1>
          <p className="mt-1 text-sm text-muted">소속 팀에 따라 볼 수 있는 팀 공개 문서와 지표 범위가 달라져요.</p>
          <label className="mt-5 block">
            <span className="mb-1 block text-xs font-semibold">이름</span>
            <input required maxLength={30} value={name} onChange={(e) => setName(e.target.value)} className="h-10 w-full rounded-lg border border-line bg-bg px-3 text-sm outline-none focus:border-action" />
          </label>
          <p className="mb-1 mt-4 text-xs font-semibold">소속 팀</p>
          <div className="grid gap-2">
            {TEAMS.map((t) => (
              <button
                type="button"
                key={t.id}
                onClick={() => setTeam(t.id)}
                className={`rounded-lg border px-3 py-2 text-left ${team === t.id ? "border-brand bg-brand-soft" : "border-line hover:bg-surface"}`}
              >
                <span className="block text-sm font-semibold">{t.label}</span>
                <span className="text-xs text-muted">{t.desc}</span>
              </button>
            ))}
          </div>
          <p className="mt-3 text-[11px] text-muted">본사 법무팀·AX 관리자 권한은 관리자가 따로 부여합니다.</p>
          {error && <p className="mt-3 rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>}
          <button disabled={busy || !name.trim()} className="mt-4 flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-brand text-sm font-semibold text-white disabled:opacity-40">
            {busy && <Loader2 className="h-4 w-4 animate-spin" />} 시작하기
          </button>
        </form>
      </main>
      <Footer />
    </div>
  );
}
