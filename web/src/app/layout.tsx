import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "가온생명 AX 어시스턴트",
  description: "약관·규정을 출처와 함께 답하는 보험사 사내 AI 어시스턴트 (포트폴리오용 가상 서비스)",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <head>
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"
        />
      </head>
      <body className="antialiased">{children}</body>
    </html>
  );
}
