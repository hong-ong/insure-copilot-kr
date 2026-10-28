// 로그인 직후 보낼 곳: 온보딩(팀·이름 입력)을 마치지 않은 사용자는 바로 /onboarding 으로 보낸다.
// 화면이 뜬 뒤 /me 응답을 보고 옮기면 메인 화면이 먼저 보였다가 넘어가므로, 콜백(서버)에서 미리 판단한다.
import type { SupabaseClient } from "@supabase/supabase-js";

export async function pathAfterLogin(supabase: SupabaseClient, userId: string): Promise<string> {
  // 프로필 행은 AI 백엔드가 첫 /me 호출 때 만든다 → 행이 없으면 신규 가입자
  const { data } = await supabase.from("profiles").select("onboarded, is_demo").eq("id", userId).maybeSingle();
  return data?.onboarded || data?.is_demo ? "/chat" : "/onboarding";
}
