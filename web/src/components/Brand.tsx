// 가온생명 자체 워드마크 (실제 보험사 로고·심볼은 쓰지 않는다).
import Link from "next/link";

export function Wordmark({ size = "md", href = "/chat" }: { size?: "sm" | "md" | "lg"; href?: string }) {
  const text = size === "lg" ? "text-2xl" : size === "sm" ? "text-sm" : "text-base";
  const dot = size === "lg" ? "h-3 w-3" : "h-2 w-2";
  return (
    <Link href={href} className={`inline-flex items-center gap-2 font-bold tracking-tight text-brand ${text}`}>
      <span className="relative inline-flex">
        <span className={`${dot} rounded-full bg-accent`} />
        <span className={`${dot} -ml-1 rounded-full bg-action opacity-80`} />
      </span>
      가온생명 <span className="font-medium text-muted">AX</span>
    </Link>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-line bg-surface px-4 py-6 text-xs text-muted">
      <div className="mx-auto flex max-w-5xl flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="space-y-1">
          <p className="font-semibold text-text">가온생명 AX 어시스턴트 · AI 기획자 포트폴리오 프로젝트</p>
          <p>
            약관·규정을 출처와 함께 답하고, 판단은 거절하며, 지표는 정의된 대로 계산하는 사내 AI 어시스턴트를 기획·구현했습니다.
          </p>
          <p>가온생명은 포트폴리오용 가상 보험사이며 실제 회사와 무관합니다. 모든 데이터는 공개 자료와 가상 데이터입니다.</p>
        </div>
        <nav className="flex flex-wrap gap-x-4 gap-y-1 md:justify-end">
          <a className="hover:text-text" href="https://github.com/hong-ong/insure-copilot-kr" target="_blank" rel="noreferrer">
            GitHub
          </a>
          <a className="hover:text-text" href="https://github.com/hong-ong/insure-copilot-kr/blob/main/docs/planning/00-portfolio-plan.md" target="_blank" rel="noreferrer">
            케이스 스터디(구성안)
          </a>
          <span className="opacity-60">3분 영상 (준비 중)</span>
          <Link className="hover:text-text" href="/about/ai">
            AI 사용 고지
          </Link>
          <span>© 2026</span>
        </nav>
      </div>
    </footer>
  );
}
