// 개인정보처리방침 (누구나 볼 수 있음). 간편로그인(Google·Kakao) 앱 등록·브랜드 인증에 필요한 공개 페이지.
import Link from "next/link";
import { Footer, Wordmark } from "@/components/Brand";

const ROWS = [
  ["서비스", "가온생명 AX 어시스턴트는 AI 기획자 포트폴리오용으로 만든 시연 서비스입니다. 가온생명은 가상 회사이며 실제 보험사와 무관합니다."],
  ["수집하는 정보", "로그인 시: 이메일 주소, 이름(닉네임), 프로필 사진 주소 — Google·카카오 간편로그인 또는 이메일 가입으로 받습니다. 이용 중: 소속 팀·역할(가입 후 선택), 질문·답변 기록, 업로드한 문서, 회의록, 답변 피드백."],
  ["이용 목적", "로그인과 본인 확인, 역할별 권한(볼 수 있는 문서·지표 범위) 적용, 대화 기록 제공, 서비스 품질 평가(답변 정확도·비용·응답시간 측정)."],
  ["보관 기간", "대화 기록은 90일 뒤 삭제합니다. 계정 정보는 탈퇴 요청 시 지체 없이 삭제합니다. 가입 없이 쓰는 데모 계정은 임시 계정이며 기록이 저장되지 않을 수 있습니다."],
  ["가려서 저장하는 정보", "질문·회의록·업로드 문서에 들어간 주민번호·연락처·계좌번호·카드번호와 특정인의 병력·진단 정보(민감정보)는 자동으로 가린 뒤 저장합니다."],
  ["처리 위탁·외부 전송", "Supabase(로그인·데이터베이스·파일 저장, 서버 인도 뭄바이 리전), Vercel(웹·API 호스팅), Google Gemini API(답변 생성·요약 — 질문과 검색된 근거 문서가 전송되며, 무료 티어 입력은 Google의 모델 개선에 쓰일 수 있습니다)."],
  ["제3자 제공", "법령에 따른 경우를 빼고 개인정보를 제3자에게 제공하거나 판매하지 않습니다. 광고·추적 목적의 쿠키를 쓰지 않으며, 로그인 유지에 필요한 쿠키만 씁니다."],
  ["이용자의 권리", "언제든 자신의 정보 열람·정정·삭제와 탈퇴를 요청할 수 있습니다. Google·카카오 계정 설정에서 이 서비스와의 연결도 직접 끊을 수 있습니다."],
  ["주의", "시연 서비스이므로 실제 고객 정보나 실제 개인정보를 입력하지 마세요."],
];

export default function Privacy() {
  return (
    <div className="flex min-h-full flex-col">
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-10">
        <Wordmark href="/login" />
        <h1 className="mt-6 text-2xl font-bold">개인정보처리방침</h1>
        <p className="mt-2 text-sm text-muted">시행일 2026년 10월 21일 · 가온생명 AX 어시스턴트</p>
        <dl className="mt-6 divide-y divide-line rounded-2xl border border-line">
          {ROWS.map(([k, v]) => (
            <div key={k} className="grid gap-1 px-5 py-4 sm:grid-cols-[160px_1fr]">
              <dt className="text-sm font-bold text-brand">{k}</dt>
              <dd className="text-sm leading-relaxed">{v}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-6 text-sm text-muted">
          문의·삭제 요청:{" "}
          <a className="text-action underline" href="https://github.com/hong-ong/insure-copilot-kr/issues" target="_blank" rel="noreferrer">
            GitHub 이슈
          </a>{" "}
          ·{" "}
          <Link href="/about/ai" className="text-action underline">
            AI 사용 고지
          </Link>
        </p>
      </main>
      <Footer />
    </div>
  );
}
