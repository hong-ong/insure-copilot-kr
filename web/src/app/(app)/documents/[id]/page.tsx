// 원문 전체 보기 (출처 칩의 "새 탭에서 열기"). ?chunk= 로 인용 조항을 표시한다.
import { DocumentViewer } from "@/components/DocumentViewer";

export default async function DocumentPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ chunk?: string; key?: string }>;
}) {
  const { id } = await params;
  const { chunk, key } = await searchParams;
  return (
    <div className="mx-auto h-full max-w-4xl">
      <DocumentViewer documentId={id} chunkId={chunk} chunkKey={key} fullPage />
    </div>
  );
}
