"""개인정보·건강정보 마스킹. 업로드 문서·회의록·질문 로그에 공통으로 적용한다.

- 개인정보: 주민등록번호, 휴대전화·전화번호, 계좌번호, 카드번호, 이메일
- 건강정보(민감정보): 질병분류코드(KCD, 예: C34.9), "OOO 고객/님 + 진단·병력" 형태의 특정인 병력

약관 본문의 "암 진단 시 보장" 같은 일반 설명은 개인 정보가 아니므로 가리지 않는다.
특정인과 연결된 건강정보만 가린다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("주민등록번호", re.compile(r"\b\d{6}\s*-\s*[1-8]\d{6}\b"), "[주민번호]"),
    ("카드번호", re.compile(r"\b\d{4}[- ]\d{4}[- ]\d{4}[- ]\d{4}\b"), "[카드번호]"),
    ("휴대전화", re.compile(r"\b01[016789][- .]?\d{3,4}[- .]?\d{4}\b"), "[연락처]"),
    ("전화번호", re.compile(r"\b0(?:2|[3-6]\d)[- .]\d{3,4}[- .]\d{4}\b"), "[연락처]"),
    ("계좌번호", re.compile(r"\b\d{3,6}-\d{2,6}-\d{2,8}(?:-\d{1,3})?\b"), "[계좌번호]"),
    ("이메일", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[이메일]"),
    ("질병코드", re.compile(r"\b[A-TV-Z]\d{2}(?:\.\d{1,2})?\b(?=[^a-zA-Z]|$)"), "[질병코드]"),
]

# "홍길동 고객은 2023년 당뇨 진단" / "김OO님 고혈압 병력" → 이름 뒤 건강정보 구간을 가린다
_PERSON_HEALTH = re.compile(
    r"([가-힣]{2,4})\s*(고객|님|씨|피보험자)(?:은|는|이|가|의)?\s*([^.\n]{0,40}?)"
    r"(진단|병력|수술|입원|투약|치료 이력|기왕증)"
)


@dataclass
class MaskResult:
    """마스킹된 텍스트와 무엇을 몇 개 가렸는지 (파싱 리포트·로그에 남긴다)."""

    text: str
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        """TODO(재홍): 무엇을 왜 하는가 한 문장"""
        return sum(self.counts.values())


def mask(text: str, *, disease_codes: bool = True) -> MaskResult:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    # 약관·법규의 별표에는 "C00~C97 악성신생물" 같은 질병코드 표가 정상 내용으로 들어 있다
    # → 약관·법규 문서는 disease_codes=False 로 호출해 질병코드는 가리지 않는다.
    counts: dict[str, int] = {}
    for name, pattern, token in _PATTERNS:
        if name == "질병코드" and not disease_codes:
            continue
        text, n = pattern.subn(token, text)
        if n:
            counts[name] = counts.get(name, 0) + n

    def _person(m: re.Match[str]) -> str:
        """TODO(재홍): 무엇을 왜 하는가 한 문장"""
        counts["특정인 건강정보"] = counts.get("특정인 건강정보", 0) + 1
        return f"{m.group(1)[0]}OO {m.group(2)} [건강정보]"

    text = _PERSON_HEALTH.sub(_person, text)
    return MaskResult(text=text, counts=counts)
