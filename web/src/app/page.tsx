// 공개 홈페이지 (로그인 전 소개). 로그인한 사용자는 미들웨어가 /chat 으로 보낸다.
// 서버에서 그려 HTML에 앱 이름·설명·개인정보처리방침 링크가 바로 담기게 한다 (구글 OAuth 브랜드 인증 요건).
import Link from "next/link";
import { BarChart3, BookOpenCheck, ShieldX } from "lucide-react";
import { Footer, Wordmark } from "@/components/Brand";

const FEATURES = [
  {
    icon: BookOpenCheck,
    title: "약관·규정을 출처와 함께",
    desc: "표준약관·보험업법·분쟁조정사례에서 근거 조항을 찾아 답하고, 문서명·조항·약관 버전을 함께 보여 줍니다.",
  },
  {
    icon: ShieldX,
    title: "판단은 거절",
    desc: "“이 고객 보험금 받을 수 있나요?” 같은 지급 판단은 하지 않고, 관련 조문과 담당 부서를 안내합니다.",
  },
  {
    icon: BarChart3,
    title: "지표는 정의된 대로",
    desc: "보수교육 이수율·13회차 유지율 등 미리 정의한 지표로 계산하고, 역할에 따라 볼 수 있는 범위를 제한합니다.",
  },
];

export default function Home() {
  return (
    <div className="flex min-h-full flex-col">
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-12">
        <Wordmark size="lg" href="/" />
        <h1 className="mt-6 text-2xl font-bold leading-snug sm:text-3xl">
          가온생명 AX — 약관·규정을 출처와 함께 답하는 사내 AI 어시스턴트
        </h1>
        <p className="mt-3 text-muted">
          보험사 AX팀이 설계사·상담원·본사 법무팀을 위해 만든 업무 도우미입니다. 가온생명은 AI 기획자 포트폴리오용
          가상 보험사이며, 모든 문서와 데이터는 공개 자료와 가상 데이터입니다.
        </p>
        <div className="mt-6 flex flex-wrap gap-2">
          <Link href="/login" className="rounded-lg bg-brand px-5 py-2.5 text-sm font-semibold text-white hover:opacity-90">
            로그인 · 가입
          </Link>
          <Link href="/login" className="rounded-lg border border-line px-5 py-2.5 text-sm font-semibold hover:bg-surface">
            가입 없이 데모로 체험
          </Link>
        </div>

        <ul className="mt-10 grid gap-3 sm:grid-cols-3">
          {FEATURES.map((f) => (
            <li key={f.title} className="rounded-2xl border border-line p-4">
              <f.icon className="h-5 w-5 text-brand" />
              <p className="mt-2 text-sm font-bold">{f.title}</p>
              <p className="mt-1 text-sm leading-relaxed text-muted">{f.desc}</p>
            </li>
          ))}
        </ul>

        <p className="mt-10 text-sm text-muted">
          Google·카카오 로그인 시 이메일·이름·프로필 사진만 받으며, 자세한 내용은{" "}
          <Link href="/about/privacy" className="text-action underline">
            개인정보처리방침
          </Link>
          과{" "}
          <Link href="/about/ai" className="text-action underline">
            AI 사용 고지
          </Link>
          에서 확인할 수 있습니다.
        </p>
      </main>
      <Footer />
    </div>
  );
}
