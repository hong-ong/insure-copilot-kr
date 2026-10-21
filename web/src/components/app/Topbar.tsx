// 상단 바: 모바일 메뉴 버튼, 데모 배너(가입 유도), 역할 배지, 알림.
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Bell, Menu } from "lucide-react";
import { useApp } from "@/components/app/AppContext";
import { supabaseBrowser } from "@/lib/supabase/client";
import { ROLE_LABEL } from "@/lib/types";

interface Noti {
  id: string;
  body: string;
  link: string | null;
  read_at: string | null;
  created_at: string;
}

export function Topbar() {
  const router = useRouter();
  const { profile, demo, setSidebarOpen } = useApp();
  const [notis, setNotis] = useState<Noti[]>([]);
  const [open, setOpen] = useState(false);
  const supabase = supabaseBrowser();

  useEffect(() => {
    if (!profile) return;
    supabase
      .from("notifications")
      .select("*")
      .eq("user_id", profile.id)
      .order("created_at", { ascending: false })
      .limit(20)
      .then(({ data }) => setNotis((data as Noti[]) || []));
  }, [profile, supabase]);

  const unread = notis.filter((n) => !n.read_at).length;

  async function signupFromDemo() {
    await supabase.auth.signOut();
    router.replace("/login?mode=signup");
  }

  async function openNoti(n: Noti) {
    setOpen(false);
    if (!n.read_at) {
      await supabase.from("notifications").update({ read_at: new Date().toISOString() }).eq("id", n.id);
      setNotis((list) => list.map((x) => (x.id === n.id ? { ...x, read_at: new Date().toISOString() } : x)));
    }
    if (n.link) router.push(n.link);
  }

  return (
    <div className="shrink-0">
      {profile?.is_demo && (
        <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 bg-brand px-4 py-2 text-center text-xs text-white">
          <span>
            데모 계정은 일부 기능만 사용할 수 있어요. 가입하면 파일 업로드·회의록·검색 기록 저장을 모두 쓸 수 있습니다.
            {demo && (
              <b className="ml-1">
                (오늘 질문 {demo.used}/{demo.limit}회)
              </b>
            )}
          </span>
          <button onClick={signupFromDemo} className="rounded-full bg-accent px-3 py-0.5 font-semibold text-white hover:brightness-105">
            3초 만에 가입하기 →
          </button>
        </div>
      )}
      <header className="flex h-12 items-center gap-2 border-b border-line px-3">
        <button className="rounded-md p-1.5 hover:bg-surface md:hidden" onClick={() => setSidebarOpen(true)} aria-label="메뉴 열기">
          <Menu className="h-5 w-5" />
        </button>
        <div className="flex-1" />
        {profile && (
          <span className="rounded-full bg-brand-soft px-2.5 py-1 text-xs font-semibold text-brand">
            {ROLE_LABEL[profile.role]}
            {profile.is_demo ? " · 데모" : ""}
          </span>
        )}
        <div className="relative">
          <button onClick={() => setOpen((v) => !v)} className="relative rounded-md p-1.5 hover:bg-surface" aria-label="알림">
            <Bell className="h-5 w-5 text-muted" />
            {unread > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-bold text-white">
                {unread}
              </span>
            )}
          </button>
          {open && (
            <div className="absolute right-0 top-10 z-40 w-80 rounded-xl border border-line bg-bg p-2 shadow-xl">
              <p className="px-2 pb-1 text-xs font-semibold text-muted">알림</p>
              {notis.length === 0 && <p className="px-2 py-4 text-sm text-muted">새 알림이 없어요.</p>}
              {notis.map((n) => (
                <button
                  key={n.id}
                  onClick={() => openNoti(n)}
                  className={`block w-full rounded-lg px-2 py-2 text-left text-sm hover:bg-surface ${n.read_at ? "text-muted" : ""}`}
                >
                  {!n.read_at && <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-action align-middle" />}
                  {n.body}
                  <span className="mt-0.5 block text-[11px] text-muted">{new Date(n.created_at).toLocaleString("ko-KR")}</span>
                </button>
              ))}
              <Link href="/inquiries" onClick={() => setOpen(false)} className="mt-1 block rounded-lg px-2 py-1.5 text-xs text-action hover:bg-surface">
                내 판단 문의 보기
              </Link>
            </div>
          )}
        </div>
      </header>
    </div>
  );
}
