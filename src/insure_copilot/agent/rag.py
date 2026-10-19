"""약관·규정 RAG 경로와 거절 경로. 둘 다 '근거 조문'을 찾아 출처로 붙인다."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from supabase import Client

from insure_copilot.llm.gateway import LLMResult, complete_json
from insure_copilot.retrieval.search import Hit, previous_versions, search

RAG_PROMPT = """당신은 가온생명 사내 AI 어시스턴트입니다. 설계사·창구 직원·본사 직원의 약관·규정 질문에 답합니다.

규칙
1. 아래 [근거]에 있는 내용으로만 답하세요. 근거에 없으면 추측하지 말고 insufficient=true 로 답하세요.
2. 문장마다 근거 번호를 [S1]처럼 붙이세요. 사용한 근거 번호를 citations 배열에 넣으세요.
3. 특정 고객의 보험금 지급 여부·보상 가능 여부를 판단하지 마세요. 일반 기준만 설명하세요.
4. 기본은 '현행' 판 근거로 답하세요. '구버전' 근거가 함께 있고 내용이 다르면, 답변 끝에
   "⚠️ OOOO.OO 이전 가입자는 가입 당시 약관(구버전)이 적용됩니다"처럼 차이를 한두 문장으로 안내하세요.
   질문이 과거 시점을 묻는다면 그 시점에 유효했던 판으로 답하세요. (기준 시점: {as_of})
5. 짧고 정확하게. 숫자(한도·횟수·기간·비율)는 근거 그대로 옮기세요. 마크다운 목록은 필요할 때만.

JSON으로만 답하세요: {{"answer": "...", "citations": ["S1"], "insufficient": false}}
"""

REFUSE_TEXT = (
    "특정 고객의 보험금 지급 여부는 제가 판단할 수 없어요. "
    "지급 여부는 사고 경위·진단 내용·가입 약관을 종합해 **심사·지급 담당 부서**가 결정합니다.\n\n"
    "판단에 참고할 수 있는 **관련 조문**을 아래에 안내해 드릴게요. 판단이 필요하면 아래 **법무팀에 문의** 버튼을 눌러 주세요."
)

OUT_OF_SCOPE_TEXT = (
    "저는 가온생명의 약관·규정과 영업·교육 지표를 안내하는 업무용 어시스턴트예요. "
    "보험 약관, 사내 규정, 회의록, 실적 지표에 대해 물어봐 주세요."
)

INSUFFICIENT_TEXT = (
    "등록된 약관·규정에서 이 질문에 답할 근거를 찾지 못했어요. "
    "질문을 조금 더 구체적으로(상품명·담보명·조항) 바꿔 보시거나, 담당 부서에 확인해 주세요."
)


@dataclass
class Answer:
    """한 경로의 답변 결과. 화면과 로그에 그대로 쓰인다."""

    content: str
    route: str
    refused: bool = False
    citations: list[Hit] = field(default_factory=list)
    llm: LLMResult | None = None
    meta: dict = field(default_factory=dict)


def _context(hits: list[Hit]) -> str:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    blocks = []
    for i, h in enumerate(hits, 1):
        status = "구버전" if h.is_expired else "현행"
        period = f"{h.effective_from or '?'} ~ {h.effective_to or '현재'}"
        blocks.append(f"[S{i}] {h.label} ({status}, 적용기간 {period})\n{h.text}")
    return "\n\n".join(blocks)


def _select_for_as_of(hits: list[Hit], as_of: str) -> list[Hit]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""

    def valid(h: Hit) -> bool:
        """TODO(재홍): 무엇을 왜 하는가 한 문장"""
        start_ok = not h.effective_from or h.effective_from <= as_of
        end_ok = not h.effective_to or as_of <= h.effective_to
        return start_ok and end_ok

    picked = [h for h in hits if valid(h)]
    return picked or hits


def answer_rag(client: Client, question: str, history: list[dict], as_of: str | None) -> Answer:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    query = search_query(question, history)
    if as_of:
        hits = _select_for_as_of(search(client, query, include_expired=True), as_of)
    else:
        hits = search(client, query)
        hits = hits + previous_versions(client, hits[:3])
    if not hits:
        return Answer(
            content=INSUFFICIENT_TEXT, route="rag", refused=True, meta={"reason": "no_hits"}
        )

    messages = [{"role": "system", "content": RAG_PROMPT.format(as_of=as_of or "현재")}]
    for h in history[-4:]:
        messages.append({"role": h["role"], "content": h["content"][:600]})
    messages.append({"role": "user", "content": f"[근거]\n{_context(hits)}\n\n[질문]\n{question}"})
    data, result = complete_json(messages, trace_name="rag_answer", max_tokens=1200)

    # 답변 검증: 근거 번호가 실제 검색 결과 안에 있어야 하고, 하나도 없으면 거절로 바꾼다.
    answer_text = (data.get("answer") or "").strip()
    refs = [str(r) for r in data.get("citations") or []] + _REF_NUM.findall(
        " ".join(_REF_GROUP.findall(answer_text))
    )
    cited: list[Hit] = []
    for ref in refs:
        digits = re.sub(r"\D", "", ref)
        idx = int(digits) - 1 if digits else -1
        if 0 <= idx < len(hits) and hits[idx] not in cited:
            cited.append(hits[idx])
    if data.get("insufficient") or not cited or not answer_text:
        return Answer(
            content=INSUFFICIENT_TEXT,
            route="rag",
            refused=True,
            citations=[],
            llm=result,
            meta={
                "reason": "verification_failed",
                "raw": json.dumps(data, ensure_ascii=False)[:500],
            },
        )
    # 본문 속 [S3] · [S1, S2] · [3] 번호를 출처 목록 순서(1, 2, ...)로 다시 매긴다
    new_num = {hits.index(h) + 1: i for i, h in enumerate(cited, 1)}

    def renumber(m: re.Match[str]) -> str:
        """TODO(재홍): 무엇을 왜 하는가 한 문장"""
        nums = [new_num.get(int(n)) for n in _REF_NUM.findall(m.group(0))]
        return "".join(f"[{n}]" for n in dict.fromkeys(nums) if n)

    answer_text = _REF_GROUP.sub(renumber, answer_text)
    return Answer(content=answer_text, route="rag", citations=cited, llm=result)


# [S1] / [S1, S3] / [S1][S2] / [2] 같은 인용 표기
_REF_GROUP = re.compile(r"\[\s*S?\d{1,2}(?:\s*[,，]\s*S?\d{1,2})*\s*\]")
_REF_NUM = re.compile(r"(\d{1,2})")


def search_query(question: str, history: list[dict]) -> str:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    # "작년에 가입한 고객은?"처럼 짧은 후속 질문은 그것만으로 검색하면 근거를 못 찾는다
    # → 직전 사용자 질문을 앞에 붙여 검색한다 (5주차 질의 재작성 실험의 가장 단순한 형태)
    previous = [h["content"] for h in history if h.get("role") == "user"]
    if previous and len(question) < 30:
        return f"{previous[-1]} {question}"
    return question


def answer_refuse(client: Client, question: str) -> Answer:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    try:
        hits = search(client, question, k=3)
    except Exception:
        hits = []
    return Answer(
        content=REFUSE_TEXT, route="refuse", refused=True, citations=hits, meta={"inquiry": True}
    )


def answer_out_of_scope() -> Answer:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    return Answer(content=OUT_OF_SCOPE_TEXT, route="out_of_scope", refused=True)
