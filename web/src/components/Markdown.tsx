// 답변·원문 공용 마크다운 렌더러. 본문의 [1] [2] 출처 번호는 클릭 가능한 칩으로 바꾼다.
"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function Markdown({
  children,
  onCite,
}: {
  children: string;
  onCite?: (rank: number) => void;
}) {
  // [1] → 링크 문법으로 바꿔 두고 a 태그 렌더에서 칩으로 그린다
  const text = onCite ? children.replace(/\[(\d{1,2})\](?!\()/g, "[$1](#cite-$1)") : children;
  return (
    <div className="prose-gaon text-[15px]">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children: c }) => {
            const m = href?.match(/^#cite-(\d+)$/);
            if (m && onCite) {
              return (
                <button
                  type="button"
                  onClick={() => onCite(Number(m[1]))}
                  className="mx-0.5 inline-flex h-[18px] min-w-[18px] -translate-y-px items-center justify-center rounded-full bg-brand-soft px-1 align-middle text-[11px] font-semibold text-brand hover:bg-brand hover:text-white"
                >
                  {m[1]}
                </button>
              );
            }
            return (
              <a href={href} target="_blank" rel="noreferrer" className="text-action underline">
                {c}
              </a>
            );
          },
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
