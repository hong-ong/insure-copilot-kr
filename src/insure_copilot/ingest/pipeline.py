"""업로드 파일 → 파싱 → 품질 판정(자동 승인) → 마스킹 → 조항 청킹 → 임베딩 → 검색 반영.

판정 기준 (구성안 §5 F2)
    한글 인식률 ≥ 90%  → 자동 승인(active)
    70% ~ 90%         → 보류(held): 업로더가 미리보기를 보고 "그래도 등록" 또는 취소
    < 70%             → 반려(rejected)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date, timedelta

from insure_copilot.config import settings
from insure_copilot.ingest import clauses, formats, masking, ocr, quality
from insure_copilot.ingest.diff import build_diffs
from insure_copilot.llm.gateway import embed
from insure_copilot.store import db

PAGE_BREAK = "\f"  # documents.markdown 안의 페이지 구분자 (원문 뷰어가 페이지 표시에 쓴다)


@dataclass
class ParseOutcome:
    """파서 판정 결과 (화면의 '파싱 리포트'에 그대로 보여 준다)."""

    file_format: str
    score: float
    verdict: str
    pages: list[str]
    ocr_used: bool = False
    issues: list[str] = field(default_factory=list)
    broken_samples: list[str] = field(default_factory=list)
    ocr_cost_usd: float = 0.0


def parse_file(file_name: str, data: bytes) -> ParseOutcome:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    if len(data) > settings.max_upload_bytes:
        return ParseOutcome("unknown", 0.0, "rejected", [], issues=["파일이 10MB를 넘습니다."])
    try:
        extracted = formats.extract(file_name, data)
    except formats.UnsupportedFormat as e:
        return ParseOutcome("unknown", 0.0, "rejected", [], issues=[str(e)])
    except Exception as e:  # 손상된 파일 등
        return ParseOutcome("unknown", 0.0, "rejected", [], issues=[f"파일을 열 수 없습니다: {e}"])

    report = quality.hangul_recognition(extracted.text)
    outcome = ParseOutcome(
        file_format=extracted.file_format,
        score=report.score,
        verdict=quality.judge(report.score, settings.approve_threshold, settings.hold_threshold),
        pages=extracted.pages,
        issues=list(extracted.issues),
        broken_samples=report.broken_samples,
    )

    # 텍스트 PDF인데 글자가 깨졌거나(글꼴 인코딩), 스캔 PDF라 글자가 없으면 → OCR로 다시 읽어 본다
    if extracted.file_format == "pdf" and outcome.verdict != "approved":
        images = formats.render_pdf_pages(data, settings.ocr_max_pages)
        total_pages = len(extracted.pages)
        try:
            ocr_texts, cost = ocr.ocr_pages(images)
        except Exception as e:
            outcome.issues.append(f"OCR 재시도 실패: {e}")
        else:
            ocr_report = quality.hangul_recognition("\n".join(ocr_texts))
            outcome.ocr_cost_usd = cost.cost_usd
            outcome.issues.append(
                f"원문 추출 인식률 {report.score:.1%} → OCR 재시도 인식률 {ocr_report.score:.1%}"
            )
            if total_pages > settings.ocr_max_pages:
                outcome.issues.append(
                    f"OCR은 앞 {settings.ocr_max_pages}쪽까지만 처리했습니다 (전체 {total_pages}쪽)."
                )
            if ocr_report.score > report.score:
                outcome.pages = ocr_texts
                outcome.score = ocr_report.score
                outcome.ocr_used = True
                outcome.broken_samples = ocr_report.broken_samples
                outcome.verdict = quality.judge(
                    ocr_report.score, settings.approve_threshold, settings.hold_threshold
                )

    if report.total_words == 0 and not outcome.ocr_used:
        outcome.issues.append("한글 본문을 찾지 못했습니다.")
    return outcome


def process_upload(document_id: str, file_name: str, data: bytes, doc_type: str) -> ParseOutcome:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    started = time.perf_counter()
    sb = db.service()
    outcome = parse_file(file_name, data)

    disease_codes = doc_type not in ("terms", "law")
    masked_pages = [
        masking.mask(p, disease_codes=disease_codes, person_health=disease_codes).text
        for p in outcome.pages
    ]
    sb.table("documents").update(
        {
            "status": {"approved": "parsing", "held": "held", "rejected": "rejected"}[
                outcome.verdict
            ],
            "markdown": PAGE_BREAK.join(masked_pages) if outcome.verdict != "rejected" else None,
        }
    ).eq("id", document_id).execute()

    n_chunks = 0
    if outcome.verdict == "approved":
        n_chunks = activate_document(document_id)

    sb.table("parse_jobs").insert(
        {
            "document_id": document_id,
            "file_format": outcome.file_format,
            "score": round(outcome.score, 4),
            "ocr_used": outcome.ocr_used,
            "verdict": outcome.verdict,
            "issues": outcome.issues + [f"깨진 어절 예: {', '.join(outcome.broken_samples[:5])}"]
            if outcome.broken_samples
            else outcome.issues,
            "pages": len(outcome.pages),
            "chars": sum(len(p) for p in outcome.pages),
            "chunks": n_chunks,
            "duration_ms": int((time.perf_counter() - started) * 1000),
        }
    ).execute()
    return outcome


def activate_document(document_id: str) -> int:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    sb = db.service()
    doc = sb.table("documents").select("*").eq("id", document_id).single().execute().data
    pages = (doc["markdown"] or "").split(PAGE_BREAK)
    text = PAGE_BREAK.join(pages)
    page_starts, pos = [], 0
    for p in pages:
        page_starts.append(pos)
        pos += len(p) + len(PAGE_BREAK)

    chunks = clauses.split_clauses(text, page_starts)
    for c in chunks:
        c.text = c.text.replace(PAGE_BREAK, "\n")
    vectors = embed([f"{doc['title']} {c.heading}\n{c.text}" for c in chunks]) if chunks else []

    sb.table("chunks").delete().eq("document_id", document_id).execute()
    rows = []
    for c, v in zip(chunks, vectors, strict=True):
        row = c.to_row()
        row.update({"document_id": document_id, "embedding": v})
        rows.append(row)
    for i in range(0, len(rows), 100):
        sb.table("chunks").insert(rows[i : i + 100]).execute()

    previous = _previous_active_version(doc)
    effective_from = doc.get("effective_from") or date.today().isoformat()
    sb.table("documents").update({"status": "active", "effective_from": effective_from}).eq(
        "id", document_id
    ).execute()
    if previous:
        end = (date.fromisoformat(effective_from) - timedelta(days=1)).isoformat()
        sb.table("documents").update({"status": "expired", "effective_to": end}).eq(
            "id", previous["id"]
        ).execute()
        build_diffs(previous["id"], document_id, doc["version_group_id"])
    return len(chunks)


def _previous_active_version(doc: dict) -> dict | None:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    rows = (
        db.service()
        .table("documents")
        .select("id, effective_from")
        .eq("version_group_id", doc["version_group_id"])
        .eq("status", "active")
        .neq("id", doc["id"])
        .order("effective_from", desc=True)
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else None
