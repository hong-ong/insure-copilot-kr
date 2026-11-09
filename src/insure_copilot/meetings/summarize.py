"""회의록(A안): 텍스트 입력 → 가온생명 표준 회의록 양식으로 AI 초안 생성 → 사용자가 확정 → 검색 대상 편입."""

from __future__ import annotations

import re

from insure_copilot.llm.gateway import LLMResult, complete_json

SUMMARY_PROMPT = """다음은 가온생명 사내 회의 기록(발언 메모 또는 녹취 텍스트)입니다. 표준 회의록 양식으로 정리하세요.

규칙
- 기록에 있는 내용만 쓰세요. 없는 결정·담당자·기한을 지어내지 마세요. 모르면 빈 문자열.
- 결정 사항은 '무엇을 하기로 했는지'가 드러나게 한 문장씩.
- 액션아이템은 할 일·담당·기한으로 나누세요.
- 개인정보·건강정보로 보이는 내용은 옮기지 마세요.

JSON으로만 답하세요:
{"overview": "회의 목적과 결론 두세 문장",
 "agenda": ["안건"],
 "decisions": ["결정 사항"],
 "action_items": [{"task": "할 일", "owner": "담당", "due": "기한"}],
 "schedule": ["향후 일정"],
 "open_issues": ["미결 사항"]}
"""

SPEAKER_RE = re.compile(
    r"^\s*([가-힣A-Za-z]{2,10}(?:\s?(?:팀장|과장|대리|차장|부장|매니저|책임|선임|님))?)\s*[:：]",
    re.M,
)


def detect_speakers(raw_text: str) -> list[str]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    return list(dict.fromkeys(m.group(1).strip() for m in SPEAKER_RE.finditer(raw_text)))


def summarize(raw_text: str, title: str) -> tuple[dict, LLMResult]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    data, result = complete_json(
        [
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": f"회의명: {title}\n\n{raw_text[:30000]}"},
        ],
        trace_name="meeting_summary",
        max_tokens=2000,
        temperature=0.1,
    )
    summary = {
        "overview": data.get("overview") or "",
        "agenda": [s for s in data.get("agenda") or [] if s],
        "decisions": [s for s in data.get("decisions") or [] if s],
        "action_items": [
            a for a in data.get("action_items") or [] if isinstance(a, dict) and a.get("task")
        ],
        "schedule": [s for s in data.get("schedule") or [] if s],
        "open_issues": [s for s in data.get("open_issues") or [] if s],
    }
    return summary, result


def to_markdown(meeting: dict) -> str:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    s = meeting.get("summary") or {}
    lines = [
        f"# 회의록 · {meeting['meeting_date']} {meeting['title']}",
        "",
        f"참석자: {', '.join(meeting.get('attendees') or []) or '-'}",
        "",
        "## 회의 개요",
        s.get("overview") or "-",
        "",
        "## 주요 안건",
        *[f"- {a}" for a in s.get("agenda") or []],
        "",
        "## 결정 사항",
        *[f"{i}. {d}" for i, d in enumerate(s.get("decisions") or [], 1)],
        "",
        "## 액션아이템",
        *[
            f"- {a.get('task')} (담당: {a.get('owner') or '-'}, 기한: {a.get('due') or '-'})"
            for a in s.get("action_items") or []
        ],
        "",
        "## 향후 일정",
        *[f"- {x}" for x in s.get("schedule") or []],
        "",
        "## 미결 사항",
        *[f"- {x}" for x in s.get("open_issues") or []],
        "",
        "## 회의 기록 원문",
        meeting.get("raw_text") or "",
    ]
    return "\n".join(lines)
