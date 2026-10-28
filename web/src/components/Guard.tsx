// 역할 확인: 권한이 없는 화면이면 안내만 보여 준다 (실제 권한은 서버 RLS·API가 다시 확인한다).
"use client";

import { Lock } from "lucide-react";
import { useApp } from "@/components/app/AppContext";
import type { Role } from "@/lib/types";

export function Guard({ roles, children }: { roles: Role[]; children: React.ReactNode }) {
  const { profile, loading } = useApp();
  if (loading || !profile) return null;
  if (!roles.includes(profile.role)) {
    return (
      <div className="mx-auto mt-24 max-w-sm text-center">
        <Lock className="mx-auto h-8 w-8 text-muted" />
        <p className="mt-3 font-semibold">이 화면을 볼 권한이 없어요</p>
        <p className="mt-1 text-sm text-muted">본사 법무팀·AX 관리자용 화면입니다. 데모 로그인 화면에서 해당 역할로 체험해 보세요.</p>
      </div>
    );
  }
  return <>{children}</>;
}

export function PageHeader({ title, desc, demoReadOnly }: { title: string; desc: string; demoReadOnly?: boolean }) {
  return (
    <div>
      <h1 className="text-xl font-bold">{title}</h1>
      <p className="mt-1 text-sm text-muted">{desc}</p>
      {demoReadOnly && <p className="mt-2 inline-block rounded-lg bg-surface px-2.5 py-1 text-xs text-muted">데모 계정은 읽기 전용이에요.</p>}
    </div>
  );
}
