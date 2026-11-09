// 왼쪽 사이드바: 1행 기능(검색·파일 업로드·회의록) / 2행 최근 검색 / 하단 프로필 메뉴.
"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  BarChart3,
  Check,
  FileDiff,
  Gavel,
  Inbox,
  LogOut,
  MessageSquareWarning,
  MoreHorizontal,
  NotebookPen,
  Pencil,
  Plus,
  Search,
  Trash2,
  Upload,
  X,
  Gauge,
  MessageCircleQuestion,
} from "lucide-react";
import { Wordmark } from "@/components/Brand";
import { useApp } from "@/components/app/AppContext";
import { supabaseBrowser } from "@/lib/supabase/client";
import { ROLE_LABEL, TEAM_LABEL } from "@/lib/types";

interface Conv {
  id: string;
  title: string;
  updated_at: string;
}

const FEATURES = [
  { href: "/chat", label: "검색", icon: Search, match: (p: string) => p.startsWith("/chat") },
  { href: "/upload", label: "파일 업로드", icon: Upload, match: (p: string) => p.startsWith("/upload") || p.startsWith("/documents") },
  { href: "/meetings", label: "회의록", icon: NotebookPen, match: (p: string) => p.startsWith("/meetings") },
];

function groupLabel(iso: string) {
  const d = new Date(iso);
  const today = new Date();
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
  const t = d.getTime();
  if (t >= start) return "오늘";
  if (t >= start - 86400000) return "어제";
  if (t >= start - 7 * 86400000) return "지난 7일";
  return "이전";
}

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { profile, convVersion, bumpConversations, setSidebarOpen } = useApp();
  const [convs, setConvs] = useState<Conv[]>([]);
  const [menuFor, setMenuFor] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [profileOpen, setProfileOpen] = useState(false);
  const supabase = supabaseBrowser();

  useEffect(() => {
    if (!profile) return;
    supabase
      .from("conversations")
      .select("id, title, updated_at")
      .eq("user_id", profile.id)
      .order("updated_at", { ascending: false })
      .limit(60)
      .then(({ data }) => setConvs((data as Conv[]) || []));
  }, [profile, convVersion, supabase]);

  const groups = useMemo(() => {
    const g: Record<string, Conv[]> = {};
    for (const c of convs) (g[groupLabel(c.updated_at)] ||= []).push(c);
    return ["오늘", "어제", "지난 7일", "이전"].filter((k) => g[k]).map((k) => [k, g[k]] as const);
  }, [convs]);

  async function rename(id: string) {
    const title = draft.trim();
    setEditing(null);
    if (!title) return;
    await supabase.from("conversations").update({ title }).eq("id", id);
    bumpConversations();
  }

  async function remove(id: string) {
    setMenuFor(null);
    if (!confirm("이 대화를 삭제할까요?")) return;
    await supabase.from("conversations").delete().eq("id", id);
    bumpConversations();
    if (pathname === `/chat/${id}`) router.push("/chat");
  }

  async function logout() {
    await supabase.auth.signOut();
    router.replace("/login");
  }

  const role = profile?.role;
  const isHq = role === "legal" || role === "ax_admin";

  return (
    <aside className="flex h-full w-[272px] flex-col border-r border-line bg-sidebar">
      <div className="flex items-center justify-between px-4 pb-2 pt-4">
        <Wordmark />
        <button className="rounded-md p-1 text-muted hover:bg-line md:hidden" onClick={() => setSidebarOpen(false)} aria-label="닫기">
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="px-3">
        <Link
          href="/chat"
          onClick={() => setSidebarOpen(false)}
          className="mt-1 flex h-10 items-center gap-2 rounded-lg border border-line bg-bg px-3 text-sm font-medium hover:border-brand"
        >
          <Plus className="h-4 w-4" /> 새 대화
        </Link>
      </div>

      {/* 1행: 기능 */}
      <nav className="mt-3 space-y-0.5 px-3" aria-label="기능">
        {FEATURES.map((f) => {
          const active = f.match(pathname);
          return (
            <Link
              key={f.href}
              href={f.href}
              onClick={() => setSidebarOpen(false)}
              className={`flex h-10 items-center gap-3 rounded-lg px-3 text-sm ${
                active ? "bg-brand-soft font-semibold text-brand" : "text-text hover:bg-line/60"
              }`}
            >
              <f.icon className="h-4 w-4" />
              {f.label}
            </Link>
          );
        })}
      </nav>

      {/* 2행: 최근 검색 */}
      <div className="mt-4 flex min-h-0 flex-1 flex-col border-t border-line pt-3">
        <p className="px-5 pb-1 text-xs font-semibold text-muted">최근 검색</p>
        <div className="scrollbar-thin min-h-0 flex-1 overflow-y-auto px-3 pb-3">
          {groups.length === 0 && <p className="px-2 py-3 text-xs text-muted">아직 검색 기록이 없어요.</p>}
          {groups.map(([label, items]) => (
            <div key={label} className="mb-2">
              <p className="px-2 pb-1 pt-2 text-[11px] text-muted">{label}</p>
              {items.map((c) => {
                const active = pathname === `/chat/${c.id}`;
                return (
                  <div key={c.id} className={`group relative flex items-center rounded-lg ${active ? "bg-line/70" : "hover:bg-line/50"}`}>
                    {editing === c.id ? (
                      <div className="flex w-full items-center gap-1 px-2 py-1">
                        <input
                          autoFocus
                          value={draft}
                          onChange={(e) => setDraft(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") rename(c.id);
                            if (e.key === "Escape") setEditing(null);
                          }}
                          className="h-7 min-w-0 flex-1 rounded border border-action bg-bg px-2 text-sm outline-none"
                        />
                        <button onClick={() => rename(c.id)} className="p-1 text-success" aria-label="저장">
                          <Check className="h-4 w-4" />
                        </button>
                      </div>
                    ) : (
                      <>
                        <Link
                          href={`/chat/${c.id}`}
                          onClick={() => setSidebarOpen(false)}
                          className="block min-w-0 flex-1 truncate px-2 py-2 text-sm"
                          title={c.title}
                        >
                          {c.title}
                        </Link>
                        <button
                          onClick={() => setMenuFor(menuFor === c.id ? null : c.id)}
                          className="mr-1 rounded p-1 text-muted opacity-0 hover:bg-line group-hover:opacity-100"
                          aria-label="대화 메뉴"
                        >
                          <MoreHorizontal className="h-4 w-4" />
                        </button>
                      </>
                    )}
                    {menuFor === c.id && (
                      <div className="absolute right-1 top-9 z-20 w-32 rounded-lg border border-line bg-bg p-1 shadow-lg">
                        <button
                          className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-surface"
                          onClick={() => {
                            setEditing(c.id);
                            setDraft(c.title);
                            setMenuFor(null);
                          }}
                        >
                          <Pencil className="h-3.5 w-3.5" /> 이름 변경
                        </button>
                        <button
                          className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-sm text-danger hover:bg-surface"
                          onClick={() => remove(c.id)}
                        >
                          <Trash2 className="h-3.5 w-3.5" /> 삭제
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* 하단: 프로필 메뉴 (법무팀·관리자 기능은 여기서 연다) */}
      <div className="relative border-t border-line p-3">
        {profileOpen && profile && (
          <div className="absolute bottom-[68px] left-3 right-3 z-30 rounded-xl border border-line bg-bg p-1.5 shadow-xl">
            <MenuLink href="/inquiries" icon={MessageCircleQuestion} label="내 판단 문의" onClick={() => setProfileOpen(false)} />
            {isHq && (
              <>
                <p className="px-2 pb-1 pt-2 text-[11px] font-semibold text-muted">본사 법무팀</p>
                <MenuLink href="/legal/inquiries" icon={Inbox} label="판단 문의함" onClick={() => setProfileOpen(false)} />
                <MenuLink href="/legal/impact" icon={FileDiff} label="개정 영향 분석" onClick={() => setProfileOpen(false)} />
                <MenuLink href="/legal/feedback" icon={MessageSquareWarning} label="피드백 검토" onClick={() => setProfileOpen(false)} />
              </>
            )}
            {role === "ax_admin" && (
              <>
                <p className="px-2 pb-1 pt-2 text-[11px] font-semibold text-muted">AX 관리자</p>
                <MenuLink href="/admin/eval" icon={Gauge} label="평가 대시보드" onClick={() => setProfileOpen(false)} />
                <MenuLink href="/admin/ops" icon={BarChart3} label="비용·토큰·로그" onClick={() => setProfileOpen(false)} />
              </>
            )}
            <div className="my-1 h-px bg-line" />
            <MenuLink href="/about/ai" icon={Gavel} label="AI 사용 고지" onClick={() => setProfileOpen(false)} />
            <button onClick={logout} className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm hover:bg-surface">
              <LogOut className="h-4 w-4" /> {profile.is_demo ? "데모 종료" : "로그아웃"}
            </button>
          </div>
        )}
        <button
          onClick={() => setProfileOpen((v) => !v)}
          className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left hover:bg-line/60"
        >
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand text-sm font-bold text-white">
            {(profile?.display_name || "?").slice(0, 1)}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-semibold">{profile?.display_name || "…"}</span>
            <span className="block truncate text-xs text-muted">
              {profile ? `${TEAM_LABEL[profile.team]} · ${ROLE_LABEL[profile.role]}` : ""}
              {profile?.is_demo ? " · 데모" : ""}
            </span>
          </span>
          <MoreHorizontal className="h-4 w-4 text-muted" />
        </button>
      </div>
    </aside>
  );
}

function MenuLink({
  href,
  icon: Icon,
  label,
  onClick,
}: {
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  onClick: () => void;
}) {
  return (
    <Link href={href} onClick={onClick} className="flex items-center gap-2 rounded-lg px-2 py-2 text-sm hover:bg-surface">
      <Icon className="h-4 w-4" /> {label}
    </Link>
  );
}
