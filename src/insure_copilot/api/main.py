"""AI 백엔드 API. 화면(Next.js)이 부르는 엔드포인트 모음.

단순 조회(대화 목록·문서 목록·피드백 목록 등)는 화면이 Supabase에서 RLS로 직접 읽고,
AI 처리·쓰기·권한 판단이 필요한 일만 여기로 온다.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from insure_copilot.agent.orchestrator import (
    DemoLimitExceeded,
    UserContext,
    demo_usage_today,
    handle_question,
)
from insure_copilot.api.deps import (
    agent_code_for,
    current_user,
    require_member,
    require_role,
    require_role_write,
)
from insure_copilot.config import settings
from insure_copilot.ingest import pipeline
from insure_copilot.ingest.masking import mask
from insure_copilot.meetings import summarize as meeting_ai
from insure_copilot.store import db

app = FastAPI(title="가온생명 AX 어시스턴트 API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)

TEAMS = {"underwriting", "claims", "education", "cs", "sales"}
DOC_TYPES = {"law", "terms", "case", "internal"}


@app.get("/health")
def health() -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    return {"ok": True, "model": settings.default_model}


# ───────────────────────── 사용자 ─────────────────────────


@app.get("/me")
def me(ctx: UserContext = Depends(current_user)) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    used = demo_usage_today(ctx.user_id) if ctx.profile.get("is_demo") else None
    return {
        "profile": ctx.profile,
        "demo": {"limit": settings.demo_daily_limit, "used": used} if used is not None else None,
    }


class DemoStart(BaseModel):
    role: Literal["agent", "legal", "ax_admin"]


DEMO_PROFILES = {
    "agent": {"team": "sales", "display_name": "데모 설계사", "agent_code": "A0007"},
    "legal": {"team": "legal", "display_name": "데모 법무팀", "agent_code": None},
    "ax_admin": {"team": "ax", "display_name": "데모 AX 관리자", "agent_code": None},
}


@app.post("/demo/start")
def demo_start(body: DemoStart, ctx: UserContext = Depends(current_user)) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    # 데모 역할은 '익명 로그인' 사용자만 받을 수 있다 → 가입 회원이 스스로 법무·관리자 권한을 얻는 길을 막는다
    if not ctx.profile.get("is_anonymous"):
        raise HTTPException(403, "데모 역할은 데모 체험 계정에서만 선택할 수 있어요.")
    profile = {
        "id": ctx.user_id,
        "role": body.role,
        "is_demo": True,
        "onboarded": True,
        **DEMO_PROFILES[body.role],
    }
    saved = db.service().table("profiles").upsert(profile).execute().data[0]
    return {"profile": saved}


class Onboarding(BaseModel):
    team: str
    display_name: str = Field(min_length=1, max_length=30)


@app.post("/onboarding")
def onboarding(body: Onboarding, ctx: UserContext = Depends(current_user)) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    if ctx.profile.get("is_demo"):
        raise HTTPException(400, "데모 계정은 온보딩이 필요 없어요.")
    if body.team not in TEAMS:
        raise HTTPException(400, "팀을 선택해 주세요.")
    update = {"team": body.team, "display_name": body.display_name.strip(), "onboarded": True}
    # 법무·AX 관리자는 가입 화면에서 고를 수 없다(관리자가 부여). 일반 가입은 설계사 또는 팀원.
    if ctx.profile.get("role") not in ("legal", "ax_admin"):
        update["role"] = "agent" if body.team == "sales" else "staff"
        update["agent_code"] = ctx.profile.get("agent_code") or agent_code_for(ctx.user_id)
    saved = db.service().table("profiles").update(update).eq("id", ctx.user_id).execute().data[0]
    return {"profile": saved}


@app.post("/notice/agree")
def agree_notice(ctx: UserContext = Depends(current_user)) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    now = datetime.now(UTC).isoformat()
    db.service().table("profiles").update({"ai_notice_agreed_at": now}).eq(
        "id", ctx.user_id
    ).execute()
    return {"ai_notice_agreed_at": now}


# ───────────────────────── 검색(채팅) ─────────────────────────


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None


@app.post("/chat")
def chat(body: ChatRequest, ctx: UserContext = Depends(current_user)) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    if not ctx.profile.get("ai_notice_agreed_at"):
        raise HTTPException(428, "AI 사용 고지에 먼저 동의해 주세요.")
    try:
        return handle_question(
            ctx, body.question.strip(), body.conversation_id, settings.demo_daily_limit
        )
    except DemoLimitExceeded as e:
        raise HTTPException(
            429,
            f"데모 계정은 하루 {settings.demo_daily_limit}회까지 질문할 수 있어요. 가입하면 제한 없이 쓸 수 있습니다.",
        ) from e
    except PermissionError as e:
        raise HTTPException(403, str(e)) from e


# ───────────────────────── 파일 업로드 ─────────────────────────


def _safe_name(name: str) -> str:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    stem = re.sub(r"[^\w.\-가-힣]", "_", name)[-80:]
    return stem or "file"


@app.post("/documents")
def upload_document(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    doc_type: str = Form("internal"),
    product: str | None = Form(None),
    visibility: Literal["all", "team"] = Form("all"),
    version_group_id: str | None = Form(None),
    version_label: str | None = Form(None),
    effective_from: str | None = Form(None),
    ctx: UserContext = Depends(require_member),
) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    data = file.file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, "파일은 10MB 이하만 올릴 수 있어요.")
    if doc_type not in DOC_TYPES:
        raise HTTPException(400, "문서 종류가 올바르지 않습니다.")
    if effective_from:
        try:
            date.fromisoformat(effective_from)
        except ValueError as e:
            raise HTTPException(400, "적용 시작일 형식은 YYYY-MM-DD 입니다.") from e

    sb = db.service()
    row = {
        "title": title.strip()[:120],
        "doc_type": doc_type,
        "product": (product or "").strip() or None,
        "visibility": visibility,
        "owner_team": ctx.profile["team"],
        "version_label": (version_label or "").strip() or None,
        "effective_from": effective_from or None,
        "status": "parsing",
        "file_name": file.filename,
        "mime_type": file.content_type,
        "size_bytes": len(data),
        "uploaded_by": ctx.user_id,
    }
    if version_group_id:
        # 새 판으로 올리려면 기존 문서를 볼 수 있어야 한다 (RLS로 확인)
        seen = (
            ctx.client.table("documents")
            .select("id")
            .eq("version_group_id", version_group_id)
            .limit(1)
            .execute()
            .data
        )
        if not seen:
            raise HTTPException(404, "새 판으로 올릴 기존 문서를 찾지 못했어요.")
        row["version_group_id"] = version_group_id
    doc = sb.table("documents").insert(row).execute().data[0]
    path = f"{ctx.user_id}/{doc['id']}/{_safe_name(file.filename or 'upload')}"
    sb.storage.from_("documents").upload(
        path, data, {"content-type": file.content_type or "application/octet-stream"}
    )
    sb.table("documents").update({"storage_path": path}).eq("id", doc["id"]).execute()

    background.add_task(_run_pipeline, doc["id"], file.filename or "upload", data, doc_type)
    return {"document_id": doc["id"], "status": "parsing"}


def _run_pipeline(document_id: str, file_name: str, data: bytes, doc_type: str) -> None:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    try:
        pipeline.process_upload(document_id, file_name, data, doc_type)
    except Exception as e:  # 파이프라인 오류도 화면에 보이게 기록
        sb = db.service()
        sb.table("documents").update({"status": "rejected"}).eq("id", document_id).execute()
        sb.table("parse_jobs").insert(
            {
                "document_id": document_id,
                "file_format": "unknown",
                "verdict": "rejected",
                "issues": [f"처리 중 오류: {e}"],
            }
        ).execute()


def _own_document(ctx: UserContext, document_id: str) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    rows = db.service().table("documents").select("*").eq("id", document_id).execute().data
    if not rows:
        raise HTTPException(404, "문서를 찾지 못했어요.")
    doc = rows[0]
    if doc["uploaded_by"] != ctx.user_id and ctx.profile.get("role") != "ax_admin":
        raise HTTPException(403, "내가 올린 문서만 처리할 수 있어요.")
    return doc


@app.post("/documents/{document_id}/activate")
def force_activate(
    document_id: str, background: BackgroundTasks, ctx: UserContext = Depends(require_member)
) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    doc = _own_document(ctx, document_id)
    if doc["status"] != "held":
        raise HTTPException(400, "보류 상태 문서만 '그래도 등록'할 수 있어요.")
    db.service().table("documents").update({"status": "parsing"}).eq("id", document_id).execute()
    background.add_task(pipeline.activate_document, document_id)
    return {"status": "parsing"}


@app.delete("/documents/{document_id}")
def cancel_document(document_id: str, ctx: UserContext = Depends(require_member)) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    doc = _own_document(ctx, document_id)
    if doc["status"] not in ("held", "rejected"):
        raise HTTPException(400, "보류·반려된 문서만 취소할 수 있어요.")
    sb = db.service()
    if doc.get("storage_path"):
        sb.storage.from_("documents").remove([doc["storage_path"]])
    sb.table("documents").delete().eq("id", document_id).execute()
    return {"deleted": True}


@app.get("/documents/{document_id}/download")
def download_url(document_id: str, ctx: UserContext = Depends(current_user)) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    rows = (
        ctx.client.table("documents")
        .select("storage_path, file_name")
        .eq("id", document_id)
        .execute()
        .data
    )
    if not rows or not rows[0].get("storage_path"):
        raise HTTPException(404, "원본 파일이 없어요.")
    signed = db.service().storage.from_("documents").create_signed_url(rows[0]["storage_path"], 300)
    return {
        "url": signed.get("signedURL") or signed.get("signedUrl"),
        "file_name": rows[0]["file_name"],
    }


@app.post("/documents/{document_id}/legal-review")
def legal_review(
    document_id: str, ctx: UserContext = Depends(require_role_write("legal", "ax_admin"))
) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    now = datetime.now(UTC).isoformat()
    db.service().table("documents").update(
        {"legal_reviewed_at": now, "legal_reviewed_by": ctx.user_id}
    ).eq("id", document_id).execute()
    return {"legal_reviewed_at": now}


def _impacted(document_id: str) -> tuple[list[dict], list[dict]]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    sb = db.service()
    diffs = (
        sb.table("document_diffs").select("*").eq("new_document_id", document_id).execute().data
        or []
    )
    if not diffs:
        return [], []
    old_id = diffs[0]["old_document_id"]
    changed = {d["chunk_key"] for d in diffs}
    cites = (
        sb.table("citations")
        .select(
            "message_id, chunk_key, label, messages(id, content, created_at, user_id, conversation_id)"
        )
        .eq("document_id", old_id)
        .execute()
        .data
        or []
    )
    impacted: dict[str, dict] = {}
    for c in cites:
        if re.sub(r"#\d+$", "", c.get("chunk_key") or "") not in changed or not c.get("messages"):
            continue
        m = c["messages"]
        item = impacted.setdefault(
            m["id"],
            {
                "message_id": m["id"],
                "user_id": m["user_id"],
                "created_at": m["created_at"],
                "answer": m["content"][:200],
                "labels": [],
            },
        )
        item["labels"].append(c["label"])
    return diffs, sorted(impacted.values(), key=lambda x: x["created_at"], reverse=True)


@app.get("/documents/{document_id}/impact")
def impact(document_id: str, ctx: UserContext = Depends(require_role("legal", "ax_admin"))) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    diffs, items = _impacted(document_id)
    return {"changed_clauses": [d["heading"] for d in diffs], "messages": items}


@app.post("/documents/{document_id}/impact/notify")
def notify_impact(
    document_id: str, ctx: UserContext = Depends(require_role_write("legal", "ax_admin"))
) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    diffs, items = _impacted(document_id)
    users = {i["user_id"] for i in items}
    if users:
        title = (
            db.service()
            .table("documents")
            .select("title, version_label")
            .eq("id", document_id)
            .single()
            .execute()
            .data
        )
        body = f"「{title['title']}」이 {title.get('version_label') or '새 판'}으로 개정되었어요. 이전에 받은 답변의 근거 조항이 바뀌었으니 다시 확인해 주세요."
        db.service().table("notifications").insert(
            [{"user_id": u, "body": body, "link": f"/documents/{document_id}/diff"} for u in users]
        ).execute()
    return {"notified": len(users)}


# ───────────────────────── 법무팀 ─────────────────────────


class InquiryCreate(BaseModel):
    message_id: str


@app.post("/inquiries")
def create_inquiry(body: InquiryCreate, ctx: UserContext = Depends(current_user)) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    sb = db.service()
    msg = sb.table("messages").select("*").eq("id", body.message_id).single().execute().data
    if not msg or msg["user_id"] != ctx.user_id:
        raise HTTPException(404, "메시지를 찾지 못했어요.")
    question = (
        sb.table("messages")
        .select("content")
        .eq("conversation_id", msg["conversation_id"])
        .eq("role", "user")
        .lt("created_at", msg["created_at"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    row = (
        sb.table("legal_inquiries")
        .insert(
            {
                "message_id": msg["id"],
                "user_id": ctx.user_id,
                "question": question[0]["content"] if question else msg["content"],
            }
        )
        .execute()
        .data[0]
    )
    return {"inquiry": row}


class InquiryAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=4000)


@app.post("/inquiries/{inquiry_id}/answer")
def answer_inquiry(
    inquiry_id: str,
    body: InquiryAnswer,
    ctx: UserContext = Depends(require_role_write("legal", "ax_admin")),
) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    sb = db.service()
    row = (
        sb.table("legal_inquiries")
        .update(
            {
                "answer": mask(body.answer).text,
                "status": "answered",
                "answered_by": ctx.user_id,
                "answered_at": datetime.now(UTC).isoformat(),
            }
        )
        .eq("id", inquiry_id)
        .execute()
        .data[0]
    )
    sb.table("notifications").insert(
        {
            "user_id": row["user_id"],
            "body": "법무팀이 판단 문의에 답변했어요.",
            "link": "/inquiries",
        }
    ).execute()
    return {"inquiry": row}


class FeedbackReview(BaseModel):
    correct_answer: str | None = None
    promote_to_golden: bool = False


@app.post("/feedback/{feedback_id}/review")
def review_feedback(
    feedback_id: str,
    body: FeedbackReview,
    ctx: UserContext = Depends(require_role_write("legal", "ax_admin")),
) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    row = (
        db.service()
        .table("feedback")
        .update(
            {
                "review_status": "resolved",
                "correct_answer": body.correct_answer,
                "promote_to_golden": body.promote_to_golden,
                "reviewed_by": ctx.user_id,
                "reviewed_at": datetime.now(UTC).isoformat(),
            }
        )
        .eq("id", feedback_id)
        .execute()
        .data[0]
    )
    return {"feedback": row}


# ───────────────────────── 회의록 ─────────────────────────


class MeetingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    meeting_date: date
    visibility: Literal["all", "team"] = "team"
    attendees: list[str] = []
    raw_text: str = Field(min_length=20, max_length=60000)


@app.post("/meetings")
def create_meeting(body: MeetingCreate, ctx: UserContext = Depends(require_member)) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    masked = mask(body.raw_text)
    summary, _ = meeting_ai.summarize(masked.text, body.title)
    attendees = body.attendees or meeting_ai.detect_speakers(masked.text)
    row = (
        db.service()
        .table("meetings")
        .insert(
            {
                "title": body.title,
                "meeting_date": body.meeting_date.isoformat(),
                "team": ctx.profile["team"],
                "visibility": body.visibility,
                "attendees": attendees,
                "raw_text": masked.text,
                "summary": summary,
                "created_by": ctx.user_id,
            }
        )
        .execute()
        .data[0]
    )
    return {"meeting": row, "masked": masked.counts}


class MeetingUpdate(BaseModel):
    title: str | None = None
    summary: dict | None = None
    attendees: list[str] | None = None
    visibility: Literal["all", "team"] | None = None


def _own_meeting(ctx: UserContext, meeting_id: str) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    rows = db.service().table("meetings").select("*").eq("id", meeting_id).execute().data
    if not rows or rows[0]["created_by"] != ctx.user_id:
        raise HTTPException(404, "회의록을 찾지 못했어요.")
    return rows[0]


@app.patch("/meetings/{meeting_id}")
def update_meeting(
    meeting_id: str, body: MeetingUpdate, ctx: UserContext = Depends(require_member)
) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    meeting = _own_meeting(ctx, meeting_id)
    if meeting["status"] == "confirmed":
        raise HTTPException(400, "확정된 회의록은 수정할 수 없어요.")
    update = {k: v for k, v in body.model_dump().items() if v is not None}
    row = db.service().table("meetings").update(update).eq("id", meeting_id).execute().data[0]
    return {"meeting": row}


@app.post("/meetings/{meeting_id}/confirm")
def confirm_meeting(
    meeting_id: str, background: BackgroundTasks, ctx: UserContext = Depends(require_member)
) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    meeting = _own_meeting(ctx, meeting_id)
    if meeting["status"] == "confirmed":
        raise HTTPException(400, "이미 확정된 회의록이에요.")
    sb = db.service()
    doc = (
        sb.table("documents")
        .insert(
            {
                "title": f"회의록 · {meeting['meeting_date']} {meeting['title']}",
                "doc_type": "meeting",
                "visibility": meeting["visibility"],
                "owner_team": meeting["team"],
                "status": "parsing",
                "effective_from": meeting["meeting_date"],
                "markdown": meeting_ai.to_markdown(meeting),
                "uploaded_by": ctx.user_id,
            }
        )
        .execute()
        .data[0]
    )
    row = (
        sb.table("meetings")
        .update(
            {
                "status": "confirmed",
                "document_id": doc["id"],
                "confirmed_by_name": ctx.profile.get("display_name"),
                "confirmed_at": datetime.now(UTC).isoformat(),
            }
        )
        .eq("id", meeting_id)
        .execute()
        .data[0]
    )
    background.add_task(pipeline.activate_document, doc["id"])
    return {"meeting": row}


# ───────────────────────── AX 관리자 ─────────────────────────


def _pct(values: list[int], q: float) -> int:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    if not values:
        return 0
    values = sorted(values)
    return values[min(len(values) - 1, int(round(q * (len(values) - 1))))]


@app.get("/admin/ops")
def admin_ops(days: int = 7, ctx: UserContext = Depends(require_role("ax_admin"))) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    sb = db.service()
    since = (datetime.now(UTC) - timedelta(days=max(1, min(days, 90)))).isoformat()
    msgs = (
        sb.table("messages")
        .select(
            "id, created_at, user_id, route, refused, model, prompt_tokens, completion_tokens, cost_usd, latency_ms, trace_id, meta"
        )
        .eq("role", "assistant")
        .gte("created_at", since)
        .order("created_at", desc=True)
        .limit(2000)
        .execute()
        .data
        or []
    )
    profiles = {
        p["id"]: p
        for p in sb.table("profiles").select("id, role, team, is_demo, display_name").execute().data
        or []
    }
    questions = {}
    if msgs:
        user_msgs = (
            sb.table("messages")
            .select("conversation_id, content, created_at, user_id")
            .eq("role", "user")
            .gte("created_at", since)
            .order("created_at", desc=True)
            .limit(2000)
            .execute()
            .data
            or []
        )
        questions = user_msgs
    fb = (
        sb.table("feedback")
        .select("message_id, rating, reasons")
        .gte("created_at", since)
        .execute()
        .data
        or []
    )
    fb_by_msg = {f["message_id"]: f for f in fb}
    jobs = (
        sb.table("parse_jobs")
        .select("*, documents(title, file_name, size_bytes)")
        .gte("created_at", since)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
        .data
        or []
    )

    def agg(rows: list[dict]) -> dict:
        """TODO(재홍): 무엇을 왜 하는가 한 문장"""
        lat = [r["latency_ms"] or 0 for r in rows]
        return {
            "queries": len(rows),
            "prompt_tokens": sum(r["prompt_tokens"] or 0 for r in rows),
            "completion_tokens": sum(r["completion_tokens"] or 0 for r in rows),
            "cost_usd": round(sum(float(r["cost_usd"] or 0) for r in rows), 6),
            "p50_ms": _pct(lat, 0.5),
            "p95_ms": _pct(lat, 0.95),
        }

    by: dict[str, dict[str, list]] = {
        "route": defaultdict(list),
        "model": defaultdict(list),
        "role": defaultdict(list),
    }
    daily: dict[str, list] = defaultdict(list)
    for m in msgs:
        by["route"][m["route"] or "-"].append(m)
        by["model"][m["model"] or "-"].append(m)
        by["role"][(profiles.get(m["user_id"]) or {}).get("role", "-")].append(m)
        daily[m["created_at"][:10]].append(m)

    thumbs_down = sum(1 for f in fb if f["rating"] == -1)
    logs = []
    for m in msgs[:100]:
        p = profiles.get(m["user_id"]) or {}
        q = next(
            (
                u["content"]
                for u in questions
                if u["user_id"] == m["user_id"] and u["created_at"] <= m["created_at"]
            ),
            "",
        )
        f = fb_by_msg.get(m["id"])
        logs.append(
            {
                "created_at": m["created_at"],
                "role": p.get("role"),
                "team": p.get("team"),
                "is_demo": p.get("is_demo"),
                "question": q[:120],
                "route": m["route"],
                "refused": m["refused"],
                "model": m["model"],
                "prompt_tokens": m["prompt_tokens"],
                "completion_tokens": m["completion_tokens"],
                "cost_usd": float(m["cost_usd"] or 0),
                "latency_ms": m["latency_ms"],
                "trace_id": m["trace_id"],
                "feedback": f["rating"] if f else None,
            }
        )
    return {
        "summary": {
            **agg(msgs),
            "thumbs_down_rate": round(thumbs_down / len(fb), 4) if fb else None,
            "feedback_count": len(fb),
        },
        "by_route": {k: agg(v) for k, v in by["route"].items()},
        "by_model": {k: agg(v) for k, v in by["model"].items()},
        "by_role": {k: agg(v) for k, v in by["role"].items()},
        "daily": [{"date": d, **agg(v)} for d, v in sorted(daily.items())],
        "logs": logs,
        "parse_jobs": [
            {
                "created_at": j["created_at"],
                "title": (j.get("documents") or {}).get("title"),
                "file_name": (j.get("documents") or {}).get("file_name"),
                "size_bytes": (j.get("documents") or {}).get("size_bytes"),
                "file_format": j["file_format"],
                "score": float(j["score"]) if j["score"] is not None else None,
                "ocr_used": j["ocr_used"],
                "verdict": j["verdict"],
                "duration_ms": j["duration_ms"],
                "chunks": j["chunks"],
            }
            for j in jobs
        ],
        "pricing": {
            "input_per_m": settings.price_input_per_m,
            "output_per_m": settings.price_output_per_m,
        },
    }
