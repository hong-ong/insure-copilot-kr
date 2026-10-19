// 화면에서 쓰는 공통 타입과 라벨.

export type Role = "agent" | "staff" | "legal" | "ax_admin";
export type Team = "underwriting" | "claims" | "education" | "cs" | "sales" | "legal" | "ax";

export interface Profile {
  id: string;
  display_name: string;
  team: Team;
  role: Role;
  agent_code: string | null;
  is_demo: boolean;
  is_anonymous?: boolean;
  onboarded: boolean;
  ai_notice_agreed_at: string | null;
}

export interface Citation {
  rank: number;
  chunk_id: string;
  document_id: string;
  chunk_key: string;
  label: string;
  title?: string;
  heading?: string;
  version_label?: string | null;
  is_expired?: boolean;
  page?: number | null;
  snippet?: string;
}

export type Route = "rag" | "genbi" | "refuse" | "out_of_scope";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  route?: Route | null;
  refused?: boolean;
  meta?: Record<string, unknown>;
  citations?: Citation[];
  created_at?: string;
  pending?: boolean;
  error?: boolean;
}

export const TEAM_LABEL: Record<Team, string> = {
  underwriting: "심사팀",
  claims: "지급팀",
  education: "교육팀",
  cs: "고객센터",
  sales: "영업팀",
  legal: "본사 법무팀",
  ax: "AX팀",
};

export const ROLE_LABEL: Record<Role, string> = {
  agent: "설계사",
  staff: "팀원",
  legal: "본사 법무팀",
  ax_admin: "AX 관리자",
};

export const ROUTE_LABEL: Record<Route, string> = {
  rag: "약관·규정",
  genbi: "지표",
  refuse: "판단 불가",
  out_of_scope: "범위 밖",
};

export const DOC_TYPE_LABEL: Record<string, string> = {
  law: "법규",
  terms: "약관",
  case: "분쟁사례",
  internal: "사내 문서",
  meeting: "회의록",
};
