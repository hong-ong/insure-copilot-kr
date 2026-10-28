// AI 사용 고지 상세 (누구나 볼 수 있음). 규제 체크리스트(7주차)와 같은 내용을 사용자 언어로 보여 준다.
import Link from "next/link";
import { Footer, Wordmark } from "@/components/Brand";

const ROWS = [
  ["사용하는 AI", "Google Gemini (Flash 계열, 무료 티어) — LiteLLM 게이트웨이를 거쳐 호출하며, 장애 시 대체 모델로 자동 전환합니다."],
  ["AI가 하는 일", "약관·규정 검색 결과를 근거로 답변 작성, 질문 분류(라우팅), 회의록 요약, 지표 질문을 정의된 지표로 매핑, 깨진 문서의 글자 인식(OCR)."],
  ["AI가 하지 않는 일", "특정 고객의 보험금 지급 여부·면책 여부·보상 금액 판단. 이런 질문은 거절하고 관련 조문과 담당 부서(법무팀 문의)를 안내합니다."],
  ["결과물 표시", "모든 답변에 'AI 생성' 표시, 회의록 요약은 'AI 생성 초안'으로 표시하고 사람이 확정한 뒤에만 검색 근거로 씁니다."],
  ["한계", "AI 답변은 틀릴 수 있습니다. 답변마다 출처(약관명·조항·판)를 붙이며, 근거를 찾지 못하면 답하지 않습니다. 고객 안내 전 반드시 원문을 확인하세요."],
  ["설명의무와의 관계", "금융소비자보호법상 설명의무는 설계사에게 있습니다. 이 서비스는 내부 참고 도구이며 고객 설명을 대신하지 않습니다."],
  ["개인정보·건강정보", "질문·회의록·업로드 문서의 주민번호·연락처·계좌번호·카드번호와 특정인의 병력·진단 정보는 자동으로 가려서 저장합니다. 대화 기록 보관 기간은 90일입니다."],
  ["데이터", "가온생명은 포트폴리오용 가상 회사입니다. 약관·사내 문서·실적 데이터는 모두 가상이며, 실제 개인정보를 넣지 마세요(무료 티어 입력은 공급자의 모델 개선에 쓰일 수 있습니다)."],
  ["근거 법령", "인공지능 발전과 신뢰 기반 조성 등에 관한 기본법(AI 기본법) 투명성 의무, 금융소비자보호법 설명의무, 개인정보 보호법(민감정보)."],
];

export default function AboutAi() {
  return (
    <div className="flex min-h-full flex-col">
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-10">
        <Wordmark href="/chat" />
        <h1 className="mt-6 text-2xl font-bold">AI 사용 고지</h1>
        <p className="mt-2 text-sm text-muted">가온생명 AX 어시스턴트가 생성형 AI를 어떻게 쓰는지 알려 드립니다.</p>
        <dl className="mt-6 divide-y divide-line rounded-2xl border border-line">
          {ROWS.map(([k, v]) => (
            <div key={k} className="grid gap-1 px-5 py-4 sm:grid-cols-[160px_1fr]">
              <dt className="text-sm font-bold text-brand">{k}</dt>
              <dd className="text-sm leading-relaxed">{v}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-6 text-sm text-muted">
          문의: 본사 법무팀 (앱 안의 &lsquo;법무팀에 문의&rsquo;) ·{" "}
          <Link href="/chat" className="text-action underline">
            어시스턴트로 돌아가기
          </Link>
        </p>
      </main>
      <Footer />
    </div>
  );
}
