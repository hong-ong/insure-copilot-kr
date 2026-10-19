// 로그인 화면 = 간단 소개 + 간편로그인(Google·Kakao) + 이메일 + 데모 체험 3종 + 푸터.
"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Briefcase, Loader2, Mail, Scale, ShieldCheck } from "lucide-react";
import { Footer, Wordmark } from "@/components/Brand";
import { supabaseBrowser } from "@/lib/supabase/client";
import { api } from "@/lib/api";

const DEMOS = [
  {
    role: "agent",
    label: "설계사로 체험",
    desc: "약관 검색·출처 확인, 판단 요구 거절, 내 실적 지표",
    icon: Briefcase,
  },
  {
    role: "legal",
    label: "본사 법무팀으로 체험",
    desc: "판단 문의함, 개정 영향 분석, 신구대비표, 피드백 검토",
    icon: Scale,
  },
  {
    role: "ax_admin",
    label: "AX 관리자로 체험",
    desc: "평가 대시보드, 비용·토큰·로그",
    icon: ShieldCheck,
  },
] as const;

function LoginInner() {
  const router = useRouter();
  const params = useSearchParams();
  const [mode, setMode] = useState<"login" | "signup">(params.get("mode") === "signup" ? "signup" : "login");
  const [showEmail, setShowEmail] = useState(params.get("mode") === "signup");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(params.get("error") ? "로그인에 실패했어요. 다시 시도해 주세요." : null);
  const [info, setInfo] = useState<string | null>(null);
  const supabase = supabaseBrowser();

  async function oauth(provider: "google" | "kakao") {
    setBusy(provider);
    setError(null);
    const { error } = await supabase.auth.signInWithOAuth({
      provider,
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
    if (error) {
      setError(error.message);
      setBusy(null);
    }
  }

  async function emailSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy("email");
    setError(null);
    setInfo(null);
    if (mode === "login") {
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) setError("이메일 또는 비밀번호가 맞지 않아요.");
      else router.replace("/chat");
    } else {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
      });
      if (error) setError(error.message);
      else if (data.session) router.replace("/onboarding");
      else setInfo("인증 메일을 보냈어요. 메일의 링크를 누르면 가입이 완료됩니다.");
    }
    setBusy(null);
  }

  async function demo(role: (typeof DEMOS)[number]["role"]) {
    setBusy(role);
    setError(null);
    try {
      const { error } = await supabase.auth.signInAnonymously();
      if (error) throw error;
      await api("/demo/start", { method: "POST", json: { role } });
      router.replace("/chat");
    } catch (e) {
      setError(e instanceof Error ? e.message : "데모 로그인에 실패했어요.");
      await supabase.auth.signOut();
      setBusy(null);
    }
  }

  return (
    <div className="flex min-h-full flex-col">
      <main className="flex flex-1 items-center justify-center px-4 py-10">
        <div className="w-full max-w-md">
          <div className="mb-8 text-center">
            <Wordmark size="lg" href="/login" />
            <h1 className="mt-5 text-xl font-bold">약관·규정을 출처와 함께 답하는 사내 AI 어시스턴트</h1>
            <p className="mt-2 text-sm text-muted">
              조항을 근거로 답하고, 보험금 지급 판단은 거절하고, 실적 지표는 정의된 대로 계산합니다.
            </p>
          </div>

          <div className="rounded-2xl border border-line bg-bg p-5 shadow-sm">
            <div className="space-y-2">
              <button
                onClick={() => oauth("google")}
                disabled={!!busy}
                className="flex h-11 w-full items-center justify-center gap-2 rounded-lg border border-line bg-bg text-sm font-medium hover:bg-surface disabled:opacity-60"
              >
                {busy === "google" ? <Loader2 className="h-4 w-4 animate-spin" /> : <GoogleIcon />}
                Google로 계속
              </button>
              <button
                onClick={() => oauth("kakao")}
                disabled={!!busy}
                className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-[#FEE500] text-sm font-medium text-[#191919] hover:brightness-95 disabled:opacity-60"
              >
                {busy === "kakao" ? <Loader2 className="h-4 w-4 animate-spin" /> : <KakaoIcon />}
                카카오로 계속
              </button>
              {!showEmail ? (
                <button
                  onClick={() => setShowEmail(true)}
                  className="flex h-11 w-full items-center justify-center gap-2 rounded-lg border border-line text-sm font-medium hover:bg-surface"
                >
                  <Mail className="h-4 w-4" /> 이메일로 계속
                </button>
              ) : (
                <form onSubmit={emailSubmit} className="space-y-2 pt-1">
                  <input
                    type="email"
                    required
                    placeholder="이메일"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="h-11 w-full rounded-lg border border-line bg-bg px-3 text-sm outline-none focus:border-action"
                  />
                  <input
                    type="password"
                    required
                    minLength={8}
                    placeholder="비밀번호 (8자 이상)"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="h-11 w-full rounded-lg border border-line bg-bg px-3 text-sm outline-none focus:border-action"
                  />
                  <button
                    type="submit"
                    disabled={!!busy}
                    className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-brand text-sm font-semibold text-white hover:opacity-90 disabled:opacity-60"
                  >
                    {busy === "email" && <Loader2 className="h-4 w-4 animate-spin" />}
                    {mode === "login" ? "로그인" : "가입하기"}
                  </button>
                  <p className="text-center text-xs text-muted">
                    {mode === "login" ? "계정이 없나요? " : "이미 계정이 있나요? "}
                    <button
                      type="button"
                      className="font-semibold text-action"
                      onClick={() => setMode(mode === "login" ? "signup" : "login")}
                    >
                      {mode === "login" ? "가입하기" : "로그인"}
                    </button>
                  </p>
                </form>
              )}
            </div>

            <div className="my-5 flex items-center gap-3 text-xs text-muted">
              <span className="h-px flex-1 bg-line" />
              또는 가입 없이 데모로 체험
              <span className="h-px flex-1 bg-line" />
            </div>

            <div className="grid gap-2">
              {DEMOS.map((d) => (
                <button
                  key={d.role}
                  onClick={() => demo(d.role)}
                  disabled={!!busy}
                  className="flex items-center gap-3 rounded-lg border border-line px-3 py-2.5 text-left hover:border-brand hover:bg-brand-soft disabled:opacity-60"
                >
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-soft text-brand">
                    {busy === d.role ? <Loader2 className="h-4 w-4 animate-spin" /> : <d.icon className="h-4 w-4" />}
                  </span>
                  <span>
                    <span className="block text-sm font-semibold">{d.label}</span>
                    <span className="block text-xs text-muted">{d.desc}</span>
                  </span>
                </button>
              ))}
            </div>
            <p className="mt-3 text-center text-xs text-muted">
              데모는 하루 10회 질문, 일부 기능만 쓸 수 있어요. 가입하면 파일 업로드·회의록·검색 기록 저장까지 모두 사용할 수 있습니다.
            </p>

            {error && <p className="mt-3 rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>}
            {info && <p className="mt-3 rounded-lg bg-accent-soft px-3 py-2 text-sm text-success">{info}</p>}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginInner />
    </Suspense>
  );
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden>
      <path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5a5.6 5.6 0 0 1-2.4 3.6v3h3.9c2.3-2.1 3.5-5.2 3.5-8.8z" />
      <path fill="#34A853" d="M12 24c3.2 0 6-1.1 8-2.9l-3.9-3c-1.1.7-2.5 1.2-4.1 1.2-3.1 0-5.8-2.1-6.7-5H1.3v3.1A12 12 0 0 0 12 24z" />
      <path fill="#FBBC05" d="M5.3 14.3a7.2 7.2 0 0 1 0-4.6V6.6h-4a12 12 0 0 0 0 10.8l4-3.1z" />
      <path fill="#EA4335" d="M12 4.8c1.8 0 3.3.6 4.6 1.8l3.4-3.4A12 12 0 0 0 1.3 6.6l4 3.1c.9-2.9 3.6-4.9 6.7-4.9z" />
    </svg>
  );
}

function KakaoIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden>
      <path fill="#191919" d="M12 3C6.5 3 2 6.5 2 10.8c0 2.8 1.9 5.2 4.7 6.6l-1 3.6c-.1.3.3.6.6.4l4.2-2.8c.5.1 1 .1 1.5.1 5.5 0 10-3.5 10-7.9S17.5 3 12 3z" />
    </svg>
  );
}
