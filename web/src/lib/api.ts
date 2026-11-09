// AI 백엔드(FastAPI) 호출. 로그인 토큰을 Authorization 헤더로 보낸다.
import { supabaseBrowser } from "@/lib/supabase/client";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function api<T = unknown>(
  path: string,
  init: RequestInit & { json?: unknown } = {},
): Promise<T> {
  const {
    data: { session },
  } = await supabaseBrowser().auth.getSession();
  const headers = new Headers(init.headers);
  if (session) headers.set("Authorization", `Bearer ${session.access_token}`);
  let body = init.body;
  if (init.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(init.json);
  }
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers, body });
  } catch {
    throw new ApiError(0, "AI 서버에 연결하지 못했어요. 무료 서버가 잠들어 있으면 깨어나는 데 30초쯤 걸릴 수 있어요.");
  }
  if (!res.ok) {
    let message = `요청 실패 (${res.status})`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") message = data.detail;
    } catch {}
    throw new ApiError(res.status, message);
  }
  return res.json() as Promise<T>;
}
