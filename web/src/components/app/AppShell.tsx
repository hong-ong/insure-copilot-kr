// ChatGPT형 3단 레이아웃: 사이드바 | 본문 | (출처 클릭 시) 원문 뷰어.
"use client";

import { AppProvider, useApp } from "@/components/app/AppContext";
import { Sidebar } from "@/components/app/Sidebar";
import { Topbar } from "@/components/app/Topbar";
import { NoticeModal } from "@/components/app/NoticeModal";
import { DocumentViewer } from "@/components/DocumentViewer";

function Shell({ children }: { children: React.ReactNode }) {
  const { viewer, closeViewer, sidebarOpen, setSidebarOpen, error } = useApp();
  return (
    <div className="flex h-dvh overflow-hidden">
      {/* 데스크톱 사이드바 */}
      <div className="hidden md:block">
        <Sidebar />
      </div>
      {/* 모바일 드로어 */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setSidebarOpen(false)} />
          <div className="relative h-full w-[272px]">
            <Sidebar />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        {error && <div className="bg-danger-soft px-4 py-2 text-center text-sm text-danger">{error}</div>}
        <main className="min-h-0 flex-1">{children}</main>
      </div>

      {viewer && (
        <>
          <div className="hidden w-[440px] shrink-0 lg:block">
            <DocumentViewer documentId={viewer.document_id} chunkId={viewer.chunk_id} onClose={closeViewer} />
          </div>
          <div className="fixed inset-0 z-40 bg-bg lg:hidden">
            <DocumentViewer documentId={viewer.document_id} chunkId={viewer.chunk_id} onClose={closeViewer} />
          </div>
        </>
      )}
      <NoticeModal />
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <AppProvider>
      <Shell>{children}</Shell>
    </AppProvider>
  );
}
