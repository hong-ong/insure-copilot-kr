"""한글 인식률 — 파싱 결과를 자동 승인할지 판정하는 기준.

정의 (docs/planning/00-portfolio-plan.md §5 F2-1)
    한글 인식률 = 정상 어절 수 / 판정 대상 어절 수

    - 판정 대상 어절: 한글 음절이 하나라도 있거나, 깨진 글자(�, 사용자 정의 영역, 제어문자 등)가 섞인 어절
    - 정상 어절: 깨진 글자가 없고, 한글 부분이 완성형 음절로만 이루어진 어절
      (형태소 분석기 Kiwi를 쓸 수 있으면 "알 수 없는 형태소"가 대부분인 어절도 비정상으로 본다)

    - 같은 음절만 3번 이상 반복되는 어절("사사사사")도 비정상

    최종 인식률 = 어절 인식률 × 글자 다양성 계수
    - 글자 다양성 계수: 한글 500자 구간마다 '서로 다른 음절 수'를 세어, 정상 문서라면 나올 만큼(구간 길이의 40%,
      최대 100개) 나오는지 본다. 구간별 min(1, 실제/기대)의 평균.

왜 다양성까지 보나 (실제 사례, 2026-10-19)
    글꼴 매핑이 깨진 PDF에서 글자를 뽑으면 "사사사사 사사 사사사"처럼 '정상 한글 음절'로만 깨질 수 있다.
    깨진 문자(�)가 하나도 없어서 어절 검사만으로는 인식률 100%가 나온다. 정상 한국어 500자에는 서로 다른
    음절이 보통 150개 이상 나오는데, 이 PDF는 1~2개뿐이다 → 다양성 계수가 0에 가까워져 반려된다.
"""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache

_HANGUL_SYLLABLE = re.compile(r"[가-힣]")
_JAMO = re.compile(r"[ᄀ-ᇿ㄰-㆏]")  # 낱자 자모 (ㄱ, ㅏ 등)


@dataclass
class QualityReport:
    """인식률과 그 근거(어절 수, 깨진 예시)."""

    score: float
    total_words: int
    good_words: int
    broken_samples: list[str] = field(default_factory=list)
    hangul_chars: int = 0
    word_score: float = 0.0
    diversity: float = 1.0

    def to_dict(self) -> dict:
        """TODO(재홍): 무엇을 왜 하는가 한 문장"""
        return {
            "score": round(self.score, 4),
            "total_words": self.total_words,
            "good_words": self.good_words,
            "broken_samples": self.broken_samples[:10],
            "hangul_chars": self.hangul_chars,
            "word_score": round(self.word_score, 4),
            "diversity": round(self.diversity, 4),
        }


def is_broken_char(ch: str) -> bool:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    if ch == "�":
        return True
    cat = unicodedata.category(ch)
    # Co: 사용자 정의 영역(글꼴 매핑 깨짐), Cs: 서로게이트, Cc: 제어문자(줄바꿈·탭 제외)
    if cat in ("Co", "Cs", "Cn"):
        return True
    if cat == "Cc" and ch not in "\n\r\t":
        return True
    # 라틴 확장 문자(ý, Ã 등)가 한글 문서 어절 안에 섞이는 건 대표적인 인코딩 깨짐 패턴 (×, ÷ 기호는 제외)
    return "À" <= ch <= "ɏ" and cat.startswith("L")


@lru_cache(maxsize=1)
def _kiwi():
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    # Kiwi 기본 모델은 메모리를 약 500MB 쓴다(실측 2026-10-19). 512MB 무료 서버에서는 KIWI_ENABLED=false 로 끄고
    # 깨진 문자·같은 음절 반복·글자 다양성 규칙만으로 판정한다 (글꼴 깨진 PDF는 이 규칙들로 잡힌다).
    if os.getenv("KIWI_ENABLED", "true").lower() in ("0", "false", "no"):
        return None
    try:
        from kiwipiepy import Kiwi

        return Kiwi()
    except Exception:  # 설치 안 됨·DLL 차단 등 → 규칙 기반만 사용
        return None


def _unknown_ratio(words: list[str]) -> list[float]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    kiwi = _kiwi()
    if kiwi is None or not words:
        return [0.0] * len(words)
    ratios = []
    for tokens in kiwi.tokenize(words):
        if not tokens:
            ratios.append(0.0)
            continue
        unknown = sum(1 for t in tokens if t.tag in ("UN",))
        ratios.append(unknown / len(tokens))
    return ratios


_REPEAT = re.compile(r"([가-힣])\1{2,}")  # 같은 음절 3번 이상 반복 (사사사)


def syllable_diversity(text: str, window: int = 500) -> float:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    syllables = _HANGUL_SYLLABLE.findall(text)
    if not syllables:
        return 0.0
    scores = []
    for i in range(0, len(syllables), window):
        chunk = syllables[i : i + window]
        if len(chunk) < 50 and scores:
            break  # 마지막 자투리 구간은 통계가 불안정해서 뺀다
        expected = min(100, 0.4 * len(chunk))
        scores.append(min(1.0, len(set(chunk)) / expected))
    return sum(scores) / len(scores)


def hangul_recognition(text: str, sample_limit: int = 20000) -> QualityReport:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    words = text.split()
    candidates: list[str] = []
    broken: list[str] = []
    for w in words:
        has_hangul = bool(_HANGUL_SYLLABLE.search(w))
        has_broken = any(is_broken_char(c) for c in w)
        if not (has_hangul or has_broken):
            continue  # 숫자·영문·기호만 있는 어절은 판정에서 제외
        candidates.append(w)
        if len(candidates) >= sample_limit:
            break

    if not candidates:
        return QualityReport(score=0.0, total_words=0, good_words=0)

    unknown = _unknown_ratio([c for c in candidates])
    good = 0
    for w, unk in zip(candidates, unknown, strict=True):
        bad = (
            any(is_broken_char(c) for c in w)
            or bool(_JAMO.search(w))
            or bool(_REPEAT.search(w))
            or unk > 0.5
        )
        if bad:
            if len(broken) < 20:
                broken.append(w)
        else:
            good += 1
    word_score = good / len(candidates)
    diversity = syllable_diversity(text)
    return QualityReport(
        score=word_score * diversity,
        total_words=len(candidates),
        good_words=good,
        broken_samples=broken,
        hangul_chars=len(_HANGUL_SYLLABLE.findall(text)),
        word_score=word_score,
        diversity=diversity,
    )


def judge(score: float, approve: float, hold: float) -> str:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    if score >= approve:
        return "approved"
    if score >= hold:
        return "held"
    return "rejected"
