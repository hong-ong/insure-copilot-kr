# [임시-AI작성 → 직접 작성으로 교체] 2주차 직접 작성 항목: 관·조·항 번호 정규식과 청크 스키마
#
# 10 → 1 방식이라 서비스가 돌아가도록 AI가 임시본을 만들었다.
# 2주차 공부 때 이 파일의 정규식(ARTICLE_RE·PARAGRAPH_RE·CHAPTER_RE·PART_RE)과 Chunk 스키마를
# 직접 다시 쓰고, 맨 위 표시를 "[직접 작성]"으로 바꾼다.
# 교체할 때 생각할 것: 제4조의2 같은 가지 조문, 항 번호(①) 없이 바로 본문인 조, 별표 안의 표, 특약마다 다시 1조부터 시작하는 번호.
"""약관·규정 텍스트를 관·조·항 단위로 나눈다."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

CHAPTER_RE = re.compile(r"^[ \t#]*(제\s*\d+\s*관)\s*(.*)$", re.M)
ARTICLE_RE = re.compile(
    r"^[ \t#]*(제\s*\d+\s*조(?:\s*의\s*\d+)?)\s*(?:[\(（【\[]\s*([^\)）】\]\n]{1,50})\s*[\)）】\]])?",
    re.M,
)
PARAGRAPH_RE = re.compile(r"(?:(?<=\n)|^)[ \t]*([①-⑳])", re.M)
PART_RE = re.compile(r"^[ \t#]*(?:<\s*)?(별표\s*\d*|[^\n]{0,30}특별약관)\s*(?:>)?\s*$", re.M)
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
MAX_CHUNK_CHARS = 1200


@dataclass
class Chunk:
    """검색·인용의 최소 단위. chunk_key는 판(버전)이 달라도 같은 조항이면 같다 → 신구대비에 쓴다."""

    chunk_key: str
    seq: int
    part: str
    chapter: str | None
    article_no: str | None
    article_title: str | None
    paragraph_no: str | None
    heading: str
    page: int | None
    char_start: int
    char_end: int
    text: str

    def to_row(self) -> dict:
        """TODO(재홍): 무엇을 왜 하는가 한 문장"""
        return asdict(self)


def _norm_article(no: str) -> str:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    return re.sub(r"\s+", "", no)


def _part_label(name: str) -> str:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    return "별표" if name.startswith("별표") else "특약"


def split_clauses(text: str, page_starts: list[int]) -> list[Chunk]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    articles = list(ARTICLE_RE.finditer(text))
    if len(articles) < 2:
        return split_sections(text, page_starts)

    chapters = [
        (m.start(), f"{_norm_article(m.group(1))} {m.group(2).strip()}".strip())
        for m in CHAPTER_RE.finditer(text)
    ]
    parts = [(m.start(), m.group(1).strip()) for m in PART_RE.finditer(text)]

    chunks: list[Chunk] = []
    seq = 0
    preamble = text[: articles[0].start()].strip()
    if len(preamble) > 40:
        chunks.append(
            _make(
                seq,
                "전문",
                "일반",
                None,
                None,
                None,
                None,
                "전문",
                0,
                articles[0].start(),
                preamble,
                page_starts,
            )
        )
        seq += 1

    for i, m in enumerate(articles):
        start = m.start()
        end = articles[i + 1].start() if i + 1 < len(articles) else len(text)
        # 다음 조 앞에 관·특약·별표 제목이 있으면 거기서 끊는다 (마지막 항에 "## 제2관 ..."이 붙지 않게)
        for at, _ in chapters + parts:
            if start < at < end:
                end = at
        body = text[start:end].strip()
        article_no = _norm_article(m.group(1))
        title = (m.group(2) or "").strip() or None
        chapter = _last_before(chapters, start)
        part_name = _last_before(parts, start)
        part = _part_label(part_name) if part_name else "본문"
        prefix = f"{part_name}:" if part_name else ""
        base_heading = f"{article_no}({title})" if title else article_no

        para_marks = list(PARAGRAPH_RE.finditer(body))
        if len(para_marks) < 2:
            for j, piece in enumerate(_split_long(body)):
                key = f"{prefix}{article_no}" + (f"#{j + 1}" if j else "")
                chunks.append(
                    _make(
                        seq,
                        key,
                        part,
                        chapter,
                        article_no,
                        title,
                        None,
                        base_heading,
                        start,
                        start + len(body),
                        piece,
                        page_starts,
                    )
                )
                seq += 1
            continue

        head = body[: para_marks[0].start()].strip()
        for k, pm in enumerate(para_marks):
            p_start = pm.start()
            p_end = para_marks[k + 1].start() if k + 1 < len(para_marks) else len(body)
            para_no = pm.group(1)
            para_text = body[p_start:p_end].strip()
            # 조 제목을 항 앞에 붙여 둬야 항만 검색돼도 무슨 조인지 알 수 있다
            full = f"{head}\n{para_text}" if head else para_text
            idx = CIRCLED.index(para_no) + 1
            for j, piece in enumerate(_split_long(full)):
                key = f"{prefix}{article_no}-{idx}" + (f"#{j + 1}" if j else "")
                chunks.append(
                    _make(
                        seq,
                        key,
                        part,
                        chapter,
                        article_no,
                        title,
                        para_no,
                        f"{base_heading} {para_no}항",
                        start + p_start,
                        start + p_end,
                        piece,
                        page_starts,
                    )
                )
                seq += 1
    return chunks


def split_sections(text: str, page_starts: list[int]) -> list[Chunk]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    # 조항이 없는 문서(영업 가이드·FAQ·회의록): 마크다운 제목(#) 단위, 길면 문단 단위로 자른다.
    heading_re = re.compile(r"^(#{1,4})\s+(.+)$", re.M)
    marks = list(heading_re.finditer(text))
    sections: list[tuple[int, int, str]] = []
    if not marks:
        sections.append((0, len(text), "본문"))
    else:
        if marks[0].start() > 0 and text[: marks[0].start()].strip():
            sections.append((0, marks[0].start(), "개요"))
        for i, m in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
            sections.append((m.start(), end, m.group(2).strip()))

    chunks: list[Chunk] = []
    seen: dict[str, int] = {}
    for start, end, title in sections:
        body = text[start:end].strip()
        if len(body) < 20:
            continue
        base = re.sub(r"\s+", " ", title)[:60]
        for j, piece in enumerate(_split_long(body)):
            key = base + (f"#{j + 1}" if j else "")
            seen[key] = seen.get(key, 0) + 1
            if seen[key] > 1:
                key = f"{key}~{seen[key]}"
            chunks.append(
                _make(
                    len(chunks),
                    key,
                    "일반",
                    None,
                    None,
                    None,
                    None,
                    title,
                    start,
                    end,
                    piece,
                    page_starts,
                )
            )
    return chunks


def _split_long(body: str) -> list[str]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    if len(body) <= MAX_CHUNK_CHARS:
        return [body]
    pieces, current = [], ""
    for para in re.split(r"\n\s*\n|\n(?=[-·•\d]+[.)]?\s)", body):
        if current and len(current) + len(para) > MAX_CHUNK_CHARS:
            pieces.append(current.strip())
            current = ""
        current += para + "\n"
    if current.strip():
        pieces.append(current.strip())
    return pieces


def _last_before(items: list[tuple[int, str]], pos: int) -> str | None:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    found = None
    for at, name in items:
        if at <= pos:
            found = name
        else:
            break
    return found


def _page_of(pos: int, page_starts: list[int]) -> int | None:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    if not page_starts:
        return None
    page = 1
    for i, s in enumerate(page_starts):
        if s <= pos:
            page = i + 1
    return page


def _make(
    seq, key, part, chapter, article_no, title, para_no, heading, start, end, text, page_starts
) -> Chunk:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    return Chunk(
        chunk_key=key,
        seq=seq,
        part=part,
        chapter=chapter,
        article_no=article_no,
        article_title=title,
        paragraph_no=para_no,
        heading=heading,
        page=_page_of(start, page_starts),
        char_start=start,
        char_end=end,
        text=text,
    )
