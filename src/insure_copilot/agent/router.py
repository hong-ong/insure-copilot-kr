# [임시-AI작성 → 직접 작성으로 교체] 7주차 직접 작성 항목: 의도 분류 프롬프트와 분기 조건
#
# 10 → 1 방식이라 서비스가 돌아가도록 AI가 임시본을 만들었다.
# 7주차 공부 때 ROUTER_PROMPT와 route_question()의 분기 조건을 직접 다시 쓰고, 맨 위 표시를 "[직접 작성]"으로 바꾼다.
# 교체할 때 생각할 것: "실비 청구하면 얼마 나와요?"(판단? 약관?), 지표+약관이 섞인 질문, 앞 대화를 이어받는 질문("그럼 작년엔?"),
# 그리고 라우팅 정답 칼럼이 있는 골든셋으로 라우팅 정확도를 측정하는 방법.
"""라우터: 질문을 약관·규정(rag) / 지표(genbi) / 판단 요구(refuse) / 범위 밖(out_of_scope)으로 보낸다."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from insure_copilot.llm.gateway import LLMResult, complete_json

ROUTES = ("rag", "genbi", "refuse", "out_of_scope")

ROUTER_PROMPT = """당신은 보험사 사내 AI 어시스턴트의 '접수 담당자'입니다. 사용자의 마지막 질문을 아래 넷 중 하나로 분류하세요.

- rag: 약관·법규·사내 규정·분쟁사례·회의록 내용을 묻는 질문. 보장 범위, 한도, 조건, 절차, 개정 내용, 결정 배경 등.
  예) "실비로 도수치료 몇 번까지 돼?", "청약철회는 며칠 안에 해야 해?", "도수치료 한도 줄인 이유가 뭐였지?"
- genbi: 실적·교육·계약 지표의 숫자를 묻는 질문. 유지율, 이수율, 불완전판매비율, 청약철회율, 신계약 건수 등.
  예) "내 13회차 유지율 알려줘", "이번 분기 지점별 보수교육 이수율", "1인당 신계약 몇 건이야?"
- refuse: 특정 고객·특정 사고에 대해 보험금 지급 여부, 보상 가능 여부, 심사 결과를 '판단'해 달라는 질문.
  예) "이 고객 보험금 받을 수 있어?", "김OO님 수술비 지급 대상인가요?", "이 건 면책이죠?"
  (일반적인 보장 기준을 묻는 것은 rag 입니다. "도수치료는 보장돼?"는 rag)
- out_of_scope: 보험 업무와 무관한 질문.

오늘 날짜: {today}
추가로, 질문이 과거 시점(예: "작년에 가입한", "개정 전", "2025년 기준")의 약관을 묻는지 판단해 as_of 에 YYYY-MM-DD로 적고, 아니면 null.

JSON으로만 답하세요: {{"route": "...", "reason": "한 문장", "as_of": null}}
"""

# LLM이 실패했을 때 쓰는 규칙 기반 예비 분기
_GENBI_HINT = re.compile(
    r"유지율|이수율|불완전판매\s*비율|청약\s*철회율|신계약\s*(건수|몇)|실적|보수교육\s*(몇|시간|남)"
)
_REFUSE_HINT = re.compile(
    r"(이|그|해당|저)\s*(고객|분|건).{0,20}(받을 수|지급|보상|면책|대상)|지급\s*(가능|대상)인지|받을 수 있(어|나|을까)"
)


@dataclass
class RouteDecision:
    """라우터 판단 결과."""

    route: str
    reason: str
    as_of: str | None
    llm: LLMResult | None


def route_question(question: str, history: list[dict]) -> RouteDecision:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    messages = [{"role": "system", "content": ROUTER_PROMPT.format(today=date.today().isoformat())}]
    for h in history[-4:]:
        messages.append({"role": h["role"], "content": h["content"][:500]})
    messages.append({"role": "user", "content": question})
    try:
        data, result = complete_json(messages, trace_name="router", max_tokens=200)
    except Exception:
        data, result = {}, None

    route = data.get("route")
    if route not in ROUTES:
        route = _fallback(question)
        reason = "규칙 기반 예비 분기"
    else:
        reason = data.get("reason") or ""
    as_of = data.get("as_of")
    if as_of and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(as_of)):
        as_of = None
    return RouteDecision(route=route, reason=reason, as_of=as_of, llm=result)


def _fallback(question: str) -> str:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    if _REFUSE_HINT.search(question):
        return "refuse"
    if _GENBI_HINT.search(question):
        return "genbi"
    return "rag"
