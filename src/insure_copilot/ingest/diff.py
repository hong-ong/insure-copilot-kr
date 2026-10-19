"""개정 신구대비표. 같은 문서의 이전 판과 새 판을 조항 키(chunk_key)로 맞춰 비교한다."""

from __future__ import annotations

import json
import re

from insure_copilot.llm.gateway import complete_json
from insure_copilot.store import db

SUMMARY_PROMPT = """보험 약관 개정 신구대비 항목들입니다. 각 항목의 변경 내용을 8자 이내 한국어 꼬리표로 요약하세요.
꼬리표 예: "한도 축소", "한도 확대", "조건 강화", "조건 완화", "부담 증가", "부담 감소", "신설", "삭제", "문구 정비".
JSON으로만 답하세요: {"items": [{"key": "...", "summary": "..."}]}

항목:
"""


def _base_key(key: str) -> str:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    return re.sub(r"#\d+$", "", key)


def _by_key(document_id: str) -> dict[str, dict]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    rows = (
        db.service()
        .table("chunks")
        .select("chunk_key, heading, text, seq")
        .eq("document_id", document_id)
        .order("seq")
        .execute()
        .data
    )
    merged: dict[str, dict] = {}
    for r in rows:
        k = _base_key(r["chunk_key"])
        if k in merged:
            merged[k]["text"] += "\n" + r["text"]
        else:
            merged[k] = {"heading": r["heading"], "text": r["text"], "seq": r["seq"]}
    return merged


def _norm(text: str) -> str:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    return re.sub(r"\s+", "", text)


def build_diffs(old_document_id: str, new_document_id: str, version_group_id: str) -> list[dict]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    old, new = _by_key(old_document_id), _by_key(new_document_id)
    rows: list[dict] = []
    for key in sorted(set(old) | set(new), key=lambda k: (new.get(k) or old.get(k))["seq"]):
        o, n = old.get(key), new.get(key)
        if key == "전문":  # 첫 조 앞 머리말(판 이름·적용일)은 판마다 당연히 달라서 비교에서 뺀다
            continue
        if o and n and _norm(o["text"]) == _norm(n["text"]):
            continue
        change = "changed" if o and n else ("added" if n else "removed")
        rows.append(
            {
                "version_group_id": version_group_id,
                "old_document_id": old_document_id,
                "new_document_id": new_document_id,
                "chunk_key": key,
                "heading": (n or o)["heading"],
                "old_text": o["text"] if o else None,
                "new_text": n["text"] if n else None,
                "change_type": change,
            }
        )

    if rows:
        summaries = _summarize(rows[:40])
        for r in rows:
            r["summary"] = summaries.get(r["chunk_key"]) or {
                "added": "신설",
                "removed": "삭제",
            }.get(r["change_type"], "내용 변경")
        sb = db.service()
        sb.table("document_diffs").delete().eq("new_document_id", new_document_id).execute()
        sb.table("document_diffs").insert(rows).execute()
    return rows


def _summarize(rows: list[dict]) -> dict[str, str]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    items = [
        {
            "key": r["chunk_key"],
            "before": (r["old_text"] or "(없음)")[:600],
            "after": (r["new_text"] or "(삭제)")[:600],
        }
        for r in rows
    ]
    try:
        data, _ = complete_json(
            [{"role": "user", "content": SUMMARY_PROMPT + json.dumps(items, ensure_ascii=False)}],
            trace_name="diff_summary",
            max_tokens=800,
        )
    except Exception:
        return {}
    return {i.get("key"): i.get("summary") for i in data.get("items", []) if i.get("key")}
