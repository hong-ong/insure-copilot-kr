"""질문 하나를 처리하는 전체 흐름: 마스킹 → 라우터 → 경로별 답변 → 답변 검증 → 저장(토큰·비용·지연·출처)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime

from supabase import Client

from insure_copilot.agent import rag
from insure_copilot.agent.router import route_question
from insure_copilot.genbi.engine import answer_metric
from insure_copilot.ingest.masking import mask
from insure_copilot.llm.gateway import LLMResult
from insure_copilot.store import db


class DemoLimitExceeded(Exception):
    """데모 계정 일일 질의 한도 초과."""


@dataclass
class UserContext:
    """요청한 사용자 정보 (토큰 검증 후 만들어짐)."""

    user_id: str
    access_token: str
    profile: dict

    @property
    def client(self) -> Client:
        """TODO(재홍): 무엇을 왜 하는가 한 문장"""
        return db.as_user(self.access_token)


def demo_usage_today(user_id: str) -> int:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    res = (
        db.service()
        .table("messages")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("role", "user")
        .gte("created_at", start)
        .execute()
    )
    return res.count or 0


def handle_question(
    ctx: UserContext, question: str, conversation_id: str | None, limit: int
) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    started = time.perf_counter()
    sb = db.service()
    if ctx.profile.get("is_demo") and demo_usage_today(ctx.user_id) >= limit:
        raise DemoLimitExceeded()

    masked = mask(question)
    q = masked.text

    if conversation_id:
        rows = (
            sb.table("conversations")
            .select("id, user_id")
            .eq("id", conversation_id)
            .limit(1)
            .execute()
            .data
        )
        if not rows or rows[0]["user_id"] != ctx.user_id:
            raise PermissionError("대화를 찾지 못했거나 다른 사용자의 대화입니다.")
    else:
        conv = (
            sb.table("conversations")
            .insert({"user_id": ctx.user_id, "title": q[:40]})
            .execute()
            .data[0]
        )
        conversation_id = conv["id"]

    history = (
        sb.table("messages")
        .select("role, content")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=True)
        .limit(6)
        .execute()
        .data
        or []
    )[::-1]

    user_msg = (
        sb.table("messages")
        .insert(
            {
                "conversation_id": conversation_id,
                "user_id": ctx.user_id,
                "role": "user",
                "content": q,
                "meta": {"masked": masked.counts},
            }
        )
        .execute()
        .data[0]
    )

    decision = route_question(q, history)
    usage = LLMResult(text="", model="")
    if decision.llm:
        usage.add(decision.llm)
        usage.model = decision.llm.model
        usage.trace_id = decision.llm.trace_id

    if decision.route == "genbi":
        metric = answer_metric(q, ctx.profile)
        answer = rag.Answer(
            content=metric.content,
            route="genbi",
            refused=not metric.ok,
            llm=metric.llm,
            meta=metric.meta,
        )
    elif decision.route == "refuse":
        answer = rag.answer_refuse(ctx.client, q)
    elif decision.route == "out_of_scope":
        answer = rag.answer_out_of_scope()
    else:
        answer = rag.answer_rag(ctx.client, q, history, decision.as_of)

    if answer.llm:
        usage.add(answer.llm)
        usage.model = answer.llm.model
    latency_ms = int((time.perf_counter() - started) * 1000)

    meta = dict(answer.meta)
    meta.update({"router_reason": decision.reason, "as_of": decision.as_of})
    assistant = (
        sb.table("messages")
        .insert(
            {
                "conversation_id": conversation_id,
                "user_id": ctx.user_id,
                "role": "assistant",
                "content": answer.content,
                "route": answer.route,
                "refused": answer.refused,
                "model": usage.model or None,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "cost_usd": round(usage.cost_usd, 8),
                "latency_ms": latency_ms,
                "trace_id": usage.trace_id,
                "meta": meta,
            }
        )
        .execute()
        .data[0]
    )

    citations = [
        {
            "message_id": assistant["id"],
            "chunk_id": h.id,
            "document_id": h.document_id,
            "chunk_key": h.chunk_key,
            "label": h.label,
            "rank": i,
        }
        for i, h in enumerate(answer.citations, 1)
    ]
    if citations:
        sb.table("citations").insert(citations).execute()
    sb.table("conversations").update({"updated_at": datetime.now(UTC).isoformat()}).eq(
        "id", conversation_id
    ).execute()

    return {
        "conversation_id": conversation_id,
        "user_message_id": user_msg["id"],
        "message": {
            "id": assistant["id"],
            "role": "assistant",
            "content": answer.content,
            "route": answer.route,
            "refused": answer.refused,
            "meta": meta,
            "created_at": assistant["created_at"],
            "citations": [citation_view(h, i) for i, h in enumerate(answer.citations, 1)],
            "usage": {
                "model": usage.model,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "cost_usd": usage.cost_usd,
                "latency_ms": latency_ms,
            },
        },
        "masked": masked.counts,
    }


def citation_view(h, rank: int) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    return {
        "rank": rank,
        "chunk_id": h.id,
        "document_id": h.document_id,
        "chunk_key": h.chunk_key,
        "label": h.label,
        "title": h.title,
        "heading": h.heading,
        "version_label": h.version_label,
        "is_expired": h.is_expired,
        "page": h.page,
        "snippet": h.text[:160],
    }
