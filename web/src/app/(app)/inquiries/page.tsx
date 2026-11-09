// 내 판단 문의: 내가 법무팀에 넘긴 질문과 답변.
"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { useApp } from "@/components/app/AppContext";
import { supabaseBrowser } from "@/lib/supabase/client";

interface Inquiry {
  id: string;
  question: string;
  status: "open" | "answered";
  answer: string | null;
  created_at: string;
}

export default function MyInquiries() {
  const { profile } = useApp();
  const supabase = supabaseBrowser();
  const [rows, setRows] = useState<Inquiry[] | null>(null);

  useEffect(() => {
    if (!profile) return;
    supabase
      .from("legal_inquiries")
      .select("*")
      .eq("user_id", profile.id)
      .order("created_at", { ascending: false })
      .then(({ data }) => setRows((data as Inquiry[]) || []));
  }, [profile, supabase]);

  return (
    <div className="scrollbar-thin h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-4 py-6">
        <h1 className="text-xl font-bold">내 판단 문의</h1>
        <p className="mt-1 text-sm text-muted">AI가 판단할 수 없어 법무팀에 넘긴 질문이에요.</p>
        {rows === null && <Loader2 className="mx-auto mt-10 h-5 w-5 animate-spin text-muted" />}
        {rows?.length === 0 && <p className="mt-6 text-sm text-muted">아직 문의한 내용이 없어요. 판단 요구로 거절된 답변의 &lsquo;법무팀에 문의&rsquo; 버튼으로 보낼 수 있어요.</p>}
        <div className="mt-4 space-y-3">
          {rows?.map((r) => (
            <div key={r.id} className="rounded-xl border border-line p-4">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs text-muted">{new Date(r.created_at).toLocaleString("ko-KR")}</p>
                <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${r.status === "answered" ? "bg-accent-soft text-success" : "bg-warning-soft text-warning"}`}>
                  {r.status === "answered" ? "답변 완료" : "답변 대기"}
                </span>
              </div>
              <p className="mt-1 font-semibold">“{r.question}”</p>
              {r.answer && <p className="mt-3 whitespace-pre-wrap rounded-lg bg-surface p-3 text-sm">{r.answer}</p>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
