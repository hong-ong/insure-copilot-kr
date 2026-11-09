"""데모 데이터 적재: 가온생명 가상 문서·개정안·회의록을 실제 파이프라인으로 올리고, 가상 데이터 마트를 만든다.

실행 (Supabase 마이그레이션 적용 + .env 설정 후):
    uv run python scripts/seed_demo.py           # 처음 한 번
    uv run python scripts/seed_demo.py --reset   # 시스템이 올린 데모 문서를 지우고 다시

실손 특약은 2025.07 판을 먼저 올리고 2026.04 판을 '새 판'으로 올린다 → 신구대비표가 자동 생성된다.
"""

from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

from insure_copilot.config import settings
from insure_copilot.genbi.mart import build_mart
from insure_copilot.ingest import pipeline
from insure_copilot.ingest.masking import mask
from insure_copilot.meetings import summarize as meeting_ai
from insure_copilot.store import db

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples"

DOCS = [
    # 파일, 제목, 종류, 상품, 공개 범위, 소유 팀, 판, 적용 시작일
    (
        "gaon-silson-rider-2025-07.md",
        "가온 실손의료비보장 특별약관",
        "terms",
        "실손의료비",
        "all",
        "legal",
        "2025.07 판",
        "2025-07-01",
    ),
    (
        "compliance-checklist.md",
        "완전판매 준법 체크리스트",
        "internal",
        None,
        "all",
        "legal",
        None,
        "2026-01-01",
    ),
    (
        "education-policy.md",
        "설계사 보수교육 운영 기준",
        "internal",
        None,
        "all",
        "education",
        None,
        "2026-01-01",
    ),
    (
        "sales-guide.md",
        "설계사 영업 가이드 — 실손·건강보험 상담",
        "internal",
        "실손의료비",
        "team",
        "sales",
        "2026.04 개정 반영",
        "2026-04-01",
    ),
    (
        "claims-faq.md",
        "보험금 청구 처리 FAQ",
        "internal",
        "실손의료비",
        "team",
        "claims",
        None,
        "2026-04-01",
    ),
]
REVISION = ("gaon-silson-rider-2026-04.md", "2026.04 판", "2026-04-01")
MEETING = ("meeting-2026-10-12-product-tf.txt", "상품개정 TF 정기회의", "2026-10-12")


def upload(file_name: str, row: dict) -> str:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    sb = db.service()
    data = (SAMPLES / file_name).read_bytes()
    row = {
        **row,
        "status": "parsing",
        "file_name": file_name,
        "mime_type": "text/markdown",
        "size_bytes": len(data),
    }
    doc = sb.table("documents").insert(row).execute().data[0]
    path = f"system/{doc['id']}/{file_name}"
    sb.storage.from_("documents").upload(path, data, {"content-type": "text/plain; charset=utf-8"})
    sb.table("documents").update({"storage_path": path}).eq("id", doc["id"]).execute()
    outcome = pipeline.process_upload(doc["id"], file_name, data, row["doc_type"])
    print(f"  {file_name}: 인식률 {outcome.score:.1%} → {outcome.verdict}")
    return doc["id"]


SAMPLE_EMAIL = "sample-agent@gaon-ax.invalid"


def _sample_user() -> str:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    sb = db.service()
    for u in sb.auth.admin.list_users():
        if u.email == SAMPLE_EMAIL:
            return u.id
    user = sb.auth.admin.create_user(
        {"email": SAMPLE_EMAIL, "password": secrets.token_urlsafe(24), "email_confirm": True}
    ).user
    sb.table("profiles").upsert(
        {
            "id": user.id,
            "display_name": "샘플 설계사(가상)",
            "team": "sales",
            "role": "agent",
            "agent_code": "A0042",
            "onboarded": True,
            "ai_notice_agreed_at": "2026-03-01T09:00:00+09:00",
        }
    ).execute()
    return user.id


def _conversation(user_id: str, at: str, question: str, answer: dict, cites: list[dict]) -> str:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    sb = db.service()
    conv = (
        sb.table("conversations")
        .insert({"user_id": user_id, "title": question[:40], "created_at": at, "updated_at": at})
        .execute()
        .data[0]
    )
    sb.table("messages").insert(
        {
            "conversation_id": conv["id"],
            "user_id": user_id,
            "role": "user",
            "content": question,
            "created_at": at,
        }
    ).execute()
    msg = (
        sb.table("messages")
        .insert(
            {
                "conversation_id": conv["id"],
                "user_id": user_id,
                "role": "assistant",
                "created_at": at,
                "model": "gemini/gemini-flash-lite-latest",
                "prompt_tokens": 1850,
                "completion_tokens": 120,
                "cost_usd": 0.00085,
                "latency_ms": 2400,
                **answer,
            }
        )
        .execute()
        .data[0]
    )
    for i, c in enumerate(cites, 1):
        sb.table("citations").insert({"message_id": msg["id"], "rank": i, **c}).execute()
    return msg["id"]


def seed_activity(old_terms_id: str) -> None:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    sb = db.service()
    uid = _sample_user()
    chunk = (
        sb.table("chunks")
        .select("id, chunk_key, heading")
        .eq("document_id", old_terms_id)
        .eq("chunk_key", "제4조-2")
        .single()
        .execute()
        .data
    )
    # ① 개정 전(2026-03)에 받은 답변 — 2025.07 판 제4조 ②항 인용 → 개정 후 '개정 영향 분석'에 잡힌다
    old_answer = _conversation(
        uid,
        "2026-03-15T10:20:00+09:00",
        "도수치료 연간 한도가 얼마야?",
        {
            "route": "rag",
            "content": "비급여 도수치료·체외충격파·증식치료는 합산해 연간 350만원 한도 내에서 최대 50회까지 보상됩니다 [1].",
        },
        [
            {
                "chunk_id": chunk["id"],
                "document_id": old_terms_id,
                "chunk_key": chunk["chunk_key"],
                "label": f"가온 실손의료비보장 특별약관 · {chunk['heading']} · 2025.07 판",
            }
        ],
    )
    # 개정 후 이 답변을 다시 본 설계사가 👎
    sb.table("feedback").insert(
        {
            "message_id": old_answer,
            "user_id": uid,
            "rating": -1,
            "reasons": ["약관 버전이 틀림"],
            "comment": "4월 개정 이후 가입자는 300만원·40회 아닌가요?",
        }
    ).execute()
    # ② 판단 요구 → 법무팀 문의 (대기)
    refuse = {
        "route": "refuse",
        "refused": True,
        "content": "특정 고객의 보험금 지급 여부는 제가 판단할 수 없어요.",
    }
    q1 = "김OO 고객 [건강정보] 도수치료 30회 받았는데 보험금 나와요?"
    m1 = _conversation(uid, "2026-10-14T14:05:00+09:00", q1, refuse, [])
    sb.table("legal_inquiries").insert({"message_id": m1, "user_id": uid, "question": q1}).execute()
    # ③ 판단 요구 → 법무팀 답변 완료
    q2 = "이 고객 피부과 레이저 시술 받았는데 실손으로 보상돼요?"
    m2 = _conversation(uid, "2026-10-08T11:30:00+09:00", q2, refuse, [])
    sb.table("legal_inquiries").insert(
        {
            "message_id": m2,
            "user_id": uid,
            "question": q2,
            "status": "answered",
            "answered_at": "2026-10-08T16:00:00+09:00",
            "answer": "가온 실손의료비 특약 제5조 ①항 2호에 따라 미용 목적의 시술은 보상하지 않습니다. "
            "다만 진단서로 치료 목적이 확인되면 보상 심사에서 판단하니, 고객에게 지급을 확답하지 말고 청구 접수를 안내해 주세요.",
        }
    ).execute()
    print("  샘플 대화 3건 · 판단 문의 2건(대기 1·답변 1) · 👎 피드백 1건")


def reset() -> None:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    sb = db.service()
    for u in sb.auth.admin.list_users():
        if u.email == SAMPLE_EMAIL:
            sb.auth.admin.delete_user(u.id)  # 대화·문의·피드백은 on delete cascade로 함께 지워진다
    docs = (
        sb.table("documents").select("id, storage_path").is_("uploaded_by", "null").execute().data
        or []
    )
    paths = [d["storage_path"] for d in docs if d.get("storage_path")]
    if paths:
        sb.storage.from_("documents").remove(paths)
    sb.table("meetings").delete().eq("is_sample", True).execute()
    for d in docs:
        sb.table("documents").delete().eq("id", d["id"]).execute()
    print(f"삭제: 문서 {len(docs)}건")


def main() -> int:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    print("1) 가상 데이터 마트", build_mart(settings.mart_path))
    if args.reset:
        reset()

    sb = db.service()
    print("2) 문서 업로드 → 파싱 → 판정 → 청킹 → 임베딩")
    ids = {}
    for file_name, title, doc_type, product, visibility, team, version, eff in DOCS:
        ids[file_name] = upload(
            file_name,
            {
                "title": title,
                "doc_type": doc_type,
                "product": product,
                "visibility": visibility,
                "owner_team": team,
                "version_label": version,
                "effective_from": eff,
            },
        )

    print(
        "2-1) 샘플 사용 기록 (개정 전 답변 · 판단 문의 · 피드백) — 법무팀·관리자 데모가 비어 보이지 않게"
    )
    seed_activity(ids[DOCS[0][0]])

    print("3) 개정안 업로드 (같은 문서의 새 판)")
    old = (
        sb.table("documents")
        .select("version_group_id")
        .eq("id", ids[DOCS[0][0]])
        .single()
        .execute()
        .data
    )
    file_name, version, eff = REVISION
    new_id = upload(
        file_name,
        {
            "title": DOCS[0][1],
            "doc_type": "terms",
            "product": "실손의료비",
            "visibility": "all",
            "owner_team": "legal",
            "version_label": version,
            "effective_from": eff,
            "version_group_id": old["version_group_id"],
        },
    )
    diffs = (
        sb.table("document_diffs")
        .select("heading, summary")
        .eq("new_document_id", new_id)
        .execute()
        .data
    )
    for d in diffs:
        print(f"  변경: {d['heading']} — {d['summary']}")

    print("4) 샘플 회의록 (AI 요약 → 확정 → 검색 편입)")
    file_name, title, meeting_date = MEETING
    raw = mask((SAMPLES / file_name).read_text(encoding="utf-8")).text
    summary, _ = meeting_ai.summarize(raw, title)
    meeting = {
        "title": title,
        "meeting_date": meeting_date,
        "team": "sales",
        "visibility": "all",
        "attendees": meeting_ai.detect_speakers(raw),
        "raw_text": raw,
        "summary": summary,
        "status": "confirmed",
        "confirmed_by_name": "김민준 팀장(가상)",
        "is_sample": True,
    }
    doc = (
        sb.table("documents")
        .insert(
            {
                "title": f"회의록 · {meeting_date} {title}",
                "doc_type": "meeting",
                "visibility": "all",
                "owner_team": "sales",
                "status": "parsing",
                "effective_from": meeting_date,
                "markdown": meeting_ai.to_markdown(meeting),
            }
        )
        .execute()
        .data[0]
    )
    meeting["document_id"] = doc["id"]
    meeting["confirmed_at"] = f"{meeting_date}T18:00:00+09:00"
    sb.table("meetings").insert(meeting).execute()
    print(f"  청크 {pipeline.activate_document(doc['id'])}개")
    print("완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
