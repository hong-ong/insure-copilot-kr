"""데모 데이터 적재: 가온생명 가상 문서·개정안·회의록을 실제 파이프라인으로 올리고, 가상 데이터 마트를 만든다.

실행 (Supabase 마이그레이션 적용 + .env 설정 후):
    uv run python scripts/seed_demo.py           # 처음 한 번
    uv run python scripts/seed_demo.py --reset   # 시스템이 올린 데모 문서를 지우고 다시

실손 특약은 2025.07 판을 먼저 올리고 2026.04 판을 '새 판'으로 올린다 → 신구대비표가 자동 생성된다.
"""

from __future__ import annotations

import argparse
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


def reset() -> None:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    sb = db.service()
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
