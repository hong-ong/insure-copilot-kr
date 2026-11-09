// AI 사용 고지 동의 모달 — AI 기본법 투명성 의무(생성형 AI 사전 고지). 동의 전에는 검색할 수 없다.
"use client";

import Link from "next/link";
import { useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { useApp } from "@/components/app/AppContext";

export const AI_NOTICE_POINTS = [
  "이 서비스는 생성형 AI(Google Gemini)를 사용해 답변·요약을 만듭니다.",
  "AI 답변은 틀릴 수 있으며, 보험금 지급 여부 등 판단을 대신하지 않습니다.",
  "AI 답변은 설계사의 고객 설명을 대신하지 않는 내부 참고 자료입니다. 고객 안내 전 반드시 출처 원문 약관을 확인하세요.",
  "입력 내용 중 개인정보·건강정보는 자동으로 가려져 저장되며, 대화 기록은 90일간 보관됩니다.",
];

export function NoticeModal() {
  const { profile, refreshMe } = useApp();
  const [checked, setChecked] = useState(false);
  const [busy, setBusy] = useState(false);
  if (!profile || profile.ai_notice_agreed_at || (!profile.is_demo && !profile.onboarded)) return null;

  async function agree() {
    setBusy(true);
    try {
      await api("/notice/agree", { method: "POST" });
      await refreshMe();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-lg rounded-2xl bg-bg p-6 shadow-2xl">
        <div className="mb-3 flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-soft text-brand">
            <Sparkles className="h-5 w-5" />
          </span>
          <h2 className="text-lg font-bold">AI 사용 안내</h2>
        </div>
        <ul className="space-y-2 text-sm leading-relaxed">
          {AI_NOTICE_POINTS.map((p) => (
            <li key={p} className="flex gap-2">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand" />
              {p}
            </li>
          ))}
        </ul>
        <p className="mt-3 text-xs text-muted">
          근거: AI 기본법(생성형 AI 사용 사전 고지·결과물 표시), 금융소비자보호법(설명의무).{" "}
          <Link href="/about/ai" className="text-action underline" target="_blank">
            자세히 보기
          </Link>
        </p>
        <label className="mt-5 flex cursor-pointer items-center gap-2 rounded-lg border border-line px-3 py-2.5 text-sm">
          <input type="checkbox" checked={checked} onChange={(e) => setChecked(e.target.checked)} className="h-4 w-4 accent-[var(--brand)]" />
          위 내용을 확인했습니다
        </label>
        <button
          disabled={!checked || busy}
          onClick={agree}
          className="mt-3 flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-brand text-sm font-semibold text-white disabled:opacity-40"
        >
          {busy && <Loader2 className="h-4 w-4 animate-spin" />}
          시작하기
        </button>
      </div>
    </div>
  );
}
