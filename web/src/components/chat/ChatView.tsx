// 검색(채팅) 화면: 대화 불러오기 · 질문 보내기 · 빈 화면 예시 질문 · 입력창 아래 AI 고지.
"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowUp, Loader2 } from "lucide-react";
import { useApp } from "@/components/app/AppContext";
import { MessageCard } from "@/components/chat/MessageCard";
import { api, ApiError } from "@/lib/api";
import { supabaseBrowser } from "@/lib/supabase/client";
import type { ChatMessage, Citation, Role } from "@/lib/types";

const EXAMPLES: Record<Role, string[]> = {
  agent: [
    "실비로 도수치료 몇 번까지 돼?",
    "작년에 가입한 고객은 도수치료 한도가 어떻게 돼?",
    "이 고객 보험금 받을 수 있어? 허리 디스크로 도수치료 30회 받았대",
    "내 13회차 유지율 알려줘",
    "도수치료 한도 줄인 이유가 뭐였지?",
    "청약철회는 언제까지 할 수 있어?",
  ],
  staff: [
    "보험금은 서류 접수하고 며칠 안에 지급돼?",
    "모바일로 청구할 때 세부내역서 사진 내도 돼?",
    "비중증 비급여 자기부담금이 얼마야?",
    "이번 분기 지점별 보수교육 이수율 보여줘",
  ],
  legal: [
    "2026.04 개정으로 실손 특약에서 뭐가 바뀌었어?",
    "불완전판매로 보는 대표 사례가 뭐야?",
    "지난 분기 지점별 불완전판매비율 보여줘",
    "이 건 면책이죠? 미용 목적 시술 같은데",
  ],
  ax_admin: [
    "이번 분기 채널별 13회차 유지율",
    "실비로 도수치료 몇 번까지 돼?",
    "AI 답변을 고객에게 그대로 보내도 돼?",
    "1인당 신계약 건수 지점별로 보여줘",
  ],
};

interface DbMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  route: ChatMessage["route"];
  refused: boolean;
  meta: Record<string, unknown>;
  created_at: string;
  citations: {
    chunk_id: string;
    document_id: string;
    chunk_key: string;
    label: string;
    rank: number;
    documents: { status: string; version_label: string | null } | null;
    chunks: { text: string; heading: string } | null;
  }[];
}

export function ChatView({ conversationId }: { conversationId?: string }) {
  const { profile, bumpConversations, refreshMe } = useApp();
  const [convId, setConvId] = useState<string | undefined>(conversationId);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [ratings, setRatings] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(!!conversationId);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLTextAreaElement>(null);
  const supabase = supabaseBrowser();

  useEffect(() => {
    if (!conversationId) return;
    (async () => {
      const { data } = await supabase
        .from("messages")
        .select(
          "id, role, content, route, refused, meta, created_at, citations(chunk_id, document_id, chunk_key, label, rank, documents(status, version_label), chunks(text, heading))",
        )
        .eq("conversation_id", conversationId)
        .order("created_at");
      const rows = (data as unknown as DbMessage[]) || [];
      setMessages(
        rows.map((r) => ({
          id: r.id,
          role: r.role,
          content: r.content,
          route: r.route,
          refused: r.refused,
          meta: r.meta,
          created_at: r.created_at,
          citations: (r.citations || [])
            .sort((a, b) => a.rank - b.rank)
            .map(
              (c): Citation => ({
                rank: c.rank,
                chunk_id: c.chunk_id,
                document_id: c.document_id,
                chunk_key: c.chunk_key,
                label: c.label,
                version_label: c.documents?.version_label,
                is_expired: c.documents?.status === "expired",
                snippet: c.chunks?.text?.slice(0, 160),
              }),
            ),
        })),
      );
      const ids = rows.filter((r) => r.role === "assistant").map((r) => r.id);
      if (ids.length) {
        const { data: fb } = await supabase.from("feedback").select("message_id, rating").in("message_id", ids);
        setRatings(Object.fromEntries((fb || []).map((f: { message_id: string; rating: number }) => [f.message_id, f.rating])));
      }
      setLoading(false);
    })();
  }, [conversationId, supabase]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send(text?: string) {
    const question = (text ?? input).trim();
    if (!question || sending) return;
    setInput("");
    setSending(true);
    const tempId = `tmp-${Date.now()}`;
    setMessages((m) => [
      ...m,
      { id: `${tempId}-u`, role: "user", content: question },
      { id: tempId, role: "assistant", content: "", pending: true },
    ]);
    try {
      const res = await api<{ conversation_id: string; user_message_id: string; message: ChatMessage }>("/chat", {
        method: "POST",
        json: { question, conversation_id: convId },
      });
      setMessages((m) => m.map((x) => (x.id === tempId ? res.message : x)));
      if (!convId) {
        setConvId(res.conversation_id);
        window.history.replaceState(null, "", `/chat/${res.conversation_id}`);
      }
      bumpConversations();
      if (profile?.is_demo) refreshMe();
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "답변을 받지 못했어요. 잠시 후 다시 시도해 주세요.";
      setMessages((m) => m.map((x) => (x.id === tempId ? { ...x, pending: false, error: true, content: msg } : x)));
    } finally {
      setSending(false);
      textRef.current?.focus();
    }
  }

  const empty = !loading && messages.length === 0;
  const examples = EXAMPLES[profile?.role || "agent"];

  return (
    <div className="flex h-full flex-col">
      <div className="scrollbar-thin min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-4 py-6">
          {loading && <Loader2 className="mx-auto mt-20 h-6 w-6 animate-spin text-muted" />}
          {empty && (
            <div className="mt-[10vh] text-center">
              <h1 className="text-2xl font-bold">무엇을 확인할까요?</h1>
              <p className="mt-2 text-sm text-muted">
                약관·규정은 조항 출처와 함께, 실적 지표는 정의된 대로 계산해 드려요. 보험금 지급 여부 판단은 하지 않습니다.
              </p>
              <div className="mx-auto mt-8 grid max-w-2xl gap-2 text-left sm:grid-cols-2">
                {examples.map((q) => (
                  <button
                    key={q}
                    onClick={() => send(q)}
                    className="rounded-xl border border-line px-4 py-3 text-sm hover:border-brand hover:bg-brand-soft"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}
          <div className="space-y-6">
            {messages.map((m) =>
              m.role === "user" ? (
                <div key={m.id} className="flex justify-end">
                  <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl bg-surface px-4 py-2.5 text-[15px]">{m.content}</div>
                </div>
              ) : (
                <MessageCard key={m.id} m={m} initialRating={ratings[m.id]} />
              ),
            )}
          </div>
          <div ref={bottomRef} />
        </div>
      </div>

      <div className="shrink-0 px-4 pb-3">
        <div className="mx-auto max-w-3xl">
          <div className="flex items-end gap-2 rounded-2xl border border-line bg-bg p-2 shadow-sm focus-within:border-brand">
            <textarea
              ref={textRef}
              rows={1}
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                e.target.style.height = "auto";
                e.target.style.height = Math.min(e.target.scrollHeight, 160) + "px";
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                  e.preventDefault();
                  send();
                }
              }}
              placeholder="약관·규정·회의록·실적 지표를 물어보세요"
              className="max-h-40 min-h-[40px] flex-1 resize-none bg-transparent px-2 py-2 text-[15px] outline-none"
            />
            <button
              onClick={() => send()}
              disabled={!input.trim() || sending}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand text-white disabled:opacity-30"
              aria-label="보내기"
            >
              {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowUp className="h-5 w-5" />}
            </button>
          </div>
          <p className="mt-1.5 text-center text-[11px] text-muted">
            AI가 생성한 답변으로 부정확할 수 있습니다. 고객 안내 전 출처 원문을 확인하세요. 개인정보·건강정보는 자동으로 가려집니다.
          </p>
        </div>
      </div>
    </div>
  );
}
