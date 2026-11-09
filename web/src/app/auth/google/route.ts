// 구글 로그인 시작: 우리 도메인으로 돌아오도록 구글 인증 화면으로 보낸다.
// Supabase 기본 OAuth는 돌아오는 주소가 <ref>.supabase.co 라서 구글 화면에 그 도메인이 앱 이름처럼 보인다.
// 그래서 코드 교환은 우리 서버(/auth/google/callback)에서 하고, 받은 ID 토큰으로 Supabase 세션을 만든다.
import { createHash, randomBytes } from "node:crypto";
import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const { origin } = new URL(request.url);
  const clientId = process.env.GOOGLE_OAUTH_CLIENT_ID;
  if (!clientId) return NextResponse.redirect(`${origin}/login?error=auth`);

  const state = randomBytes(16).toString("hex");
  // Supabase는 원본 nonce를 받아 해시를 ID 토큰 안의 nonce와 비교한다 → 구글에는 해시를 보낸다
  const nonce = randomBytes(16).toString("hex");
  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: `${origin}/auth/google/callback`,
    response_type: "code",
    scope: "openid email profile",
    state,
    nonce: createHash("sha256").update(nonce).digest("hex"),
    prompt: "select_account",
  });

  const res = NextResponse.redirect(`https://accounts.google.com/o/oauth2/v2/auth?${params}`);
  const cookie = { httpOnly: true, secure: origin.startsWith("https"), sameSite: "lax" as const, path: "/auth/google", maxAge: 600 };
  res.cookies.set("g_state", state, cookie);
  res.cookies.set("g_nonce", nonce, cookie);
  return res;
}
