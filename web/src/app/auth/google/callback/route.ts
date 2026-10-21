// 구글이 돌려준 코드를 ID 토큰으로 바꾸고, 그 토큰으로 Supabase 세션(쿠키)을 만든 뒤 앱으로 보낸다.
import { NextResponse, type NextRequest } from "next/server";
import { supabaseServer } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url);
  const fail = (reason: string) => {
    console.error("google login failed:", reason);
    const res = NextResponse.redirect(`${origin}/login?error=auth`);
    res.cookies.delete({ name: "g_state", path: "/auth/google" });
    res.cookies.delete({ name: "g_nonce", path: "/auth/google" });
    return res;
  };

  const code = searchParams.get("code");
  const state = searchParams.get("state");
  const nonce = request.cookies.get("g_nonce")?.value;
  if (!code || !state || state !== request.cookies.get("g_state")?.value || !nonce) {
    return fail(searchParams.get("error") ?? "state mismatch");
  }

  const tokenRes = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      code,
      client_id: process.env.GOOGLE_OAUTH_CLIENT_ID!,
      client_secret: process.env.GOOGLE_OAUTH_CLIENT_SECRET!,
      redirect_uri: `${origin}/auth/google/callback`,
      grant_type: "authorization_code",
    }),
  });
  const token = await tokenRes.json();
  if (!tokenRes.ok || !token.id_token) return fail(`token exchange ${tokenRes.status} ${token.error ?? ""}`);

  const supabase = await supabaseServer();
  const { error } = await supabase.auth.signInWithIdToken({ provider: "google", token: token.id_token, nonce });
  if (error) return fail(`supabase ${error.message}`);

  const res = NextResponse.redirect(`${origin}/chat`);
  res.cookies.delete({ name: "g_state", path: "/auth/google" });
  res.cookies.delete({ name: "g_nonce", path: "/auth/google" });
  return res;
}
