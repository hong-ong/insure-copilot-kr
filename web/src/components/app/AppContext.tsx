// 앱 전역 상태: 내 프로필, 데모 사용량, 최근 검색 새로고침 신호, 우측 원문 뷰어.
"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Citation, Profile } from "@/lib/types";

interface DemoUsage {
  limit: number;
  used: number;
}

interface AppState {
  profile: Profile | null;
  demo: DemoUsage | null;
  loading: boolean;
  error: string | null;
  refreshMe: () => Promise<void>;
  convVersion: number;
  bumpConversations: () => void;
  viewer: Citation | null;
  openViewer: (c: Citation) => void;
  closeViewer: () => void;
  sidebarOpen: boolean;
  setSidebarOpen: (v: boolean) => void;
}

const Ctx = createContext<AppState | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [demo, setDemo] = useState<DemoUsage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [convVersion, setConvVersion] = useState(0);
  const [viewer, setViewer] = useState<Citation | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const refreshMe = useCallback(async () => {
    try {
      const me = await api<{ profile: Profile; demo: DemoUsage | null }>("/me");
      setProfile(me.profile);
      setDemo(me.demo);
      setError(null);
      if (!me.profile.is_demo && !me.profile.onboarded) router.replace("/onboarding");
    } catch (e) {
      setError(e instanceof Error ? e.message : "프로필을 불러오지 못했어요.");
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    refreshMe();
  }, [refreshMe]);

  return (
    <Ctx.Provider
      value={{
        profile,
        demo,
        loading,
        error,
        refreshMe,
        convVersion,
        bumpConversations: () => setConvVersion((v) => v + 1),
        viewer,
        openViewer: setViewer,
        closeViewer: () => setViewer(null),
        sidebarOpen,
        setSidebarOpen,
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export function useApp() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useApp must be used inside AppProvider");
  return v;
}
