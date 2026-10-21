// OAuth(Google·Kakao)·이메일 인증 후 돌아오는 곳: 코드를 세션으로 바꾸고 앱으로 보낸다.
import { NextResponse } from "next/server";
import { supabaseServer } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  if (code) {
    const supabase = await supabaseServer();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) return NextResponse.redirect(`${origin}/chat`);
  }
  return NextResponse.redirect(`${origin}/login?error=auth`);
}
