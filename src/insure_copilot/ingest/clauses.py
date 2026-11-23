# [임시-AI작성 → 직접 작성으로 교체] 2주차 직접 작성 항목: 관·조·항 번호 정규식과 청크 스키마
#
# 10 → 1 방식이라 서비스가 돌아가도록 AI가 임시본을 만들었다.
# 2주차 공부 때 이 파일의 정규식(ARTICLE_RE·PARAGRAPH_RE·CHAPTER_RE·PART_RE)과 Chunk 스키마를
# 직접 다시 쓰고, 맨 위 표시를 "[직접 작성]"으로 바꾼다.
# 교체할 때 생각할 것: 제4조의2 같은 가지 조문, 항 번호(①) 없이 바로 본문인 조, 별표 안의 표, 특약마다 다시 1조부터 시작하는 번호.
"""약관·규정 텍스트를 관·조·항 단위로 나눈다."""

from __future__ import annotations

import bisect
import re
from dataclasses import asdict, dataclass

CHAPTER_RE = re.compile(r"^[ \t\f#]*(제\s*\d+\s*관)\s*(.*)$", re.M)
ARTICLE_RE = re.compile(
    r"^[ \t\f#]*(제\s*\d+\s*조(?:\s*의\s*\d+)?)\s*(?:[\(（【\[]\s*([^\)）】\]\n]{1,50})\s*[\)）】\]])?",
    re.M,
)
PARAGRAPH_RE = re.compile(r"(?:(?<=\n)|^)[ \t\f]*([①-⑳])", re.M)
PART_RE = re.compile(r"^[ \t\f#]*(?:<\s*)?(별표\s*\d*|[^\n]{0,30}특별약관)\s*(?:>)?\s*$", re.M)
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
    section: str | None = None  # 구획 이름 (주계약 · 특약 이름 · 별표 · 부록)

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
    sections = find_sections(text)
    if not sections:
        return _split_flat(text, page_starts)
    return _split_structured(text, page_starts, sections)


# ───────────────── 통합약관 구조 인식 (주계약 + 특약 N개 + 별표 + 부록) ─────────────────
# 실제 보험사 통합약관(교보생명 공시 약관으로 확인)은 주계약 뒤에 특약 수십 개가 붙고,
# 특약마다 "제1관 목적 및 용어의 정의 → 제1조(목적)"부터 번호가 다시 시작한다.
# 그래서 조 번호만으로 키를 만들면 특약끼리 겹친다 → 먼저 구획을 나누고, 키에 구획 이름을 붙인다.

# 구획 시작: 줄 하나에 "제N조(목적)" 또는 "제N조(보장종목)"(실손 표준 구조)만 있는 줄.
# 대부분 제1조지만, 주피형·종피형 특약은 앞 번호를 이어 "제21조(목적)"으로 시작하기도 한다 (목차 줄은 뒤에 쪽번호·점선이 붙어 여기에 안 걸린다)
SECTION_START_RE = re.compile(
    r"^[ \t\f]*제\s*\d+\s*조\s*[\(（]\s*(?:목\s*적|보\s*장\s*종\s*목)\s*[\)）][ \t]*$", re.M
)
# 특약 적용 문장: "이 특약의 약관은 무배당11대피부질환입원특약을 선택하여 가입한 경우에 한하여 적용합니다"
RIDER_SENTENCE_RE = re.compile(
    r"이\s*특\s*약\s*의\s*약\s*관\s*은\s*(.+?)\s*[을를]\s*(?:각\s*각\s*)?선\s*택\s*하\s*여", re.S
)
# 구조 조항: "제N조(제목)" 또는 "제N조의M(제목)" 이 한 줄(제목이 다음 줄로 넘어가도 됨)을 차지
STRUCT_ARTICLE_RE = re.compile(
    # 제목 괄호는 ( ) 또는 [ ] — 제목 안에 "(독촉)" 같은 괄호가 한 겹 더 있을 수 있다
    r"^[ \t\f]*(제\s*(\d+)\s*조(?:\s*의\s*(\d+))?)\s*[\(（\[]"
    r"((?:[^()（）\[\]]|[\(（][^()（）\n]{0,30}[\)）]){1,120}?)[\)）\]][ \t]*$",
    re.M,
)
# 별표·부표·별첨 제목: "(별표3)", "( 별표3 )", "<부표9-1>" 로 시작하는 짧은 줄
APPENDIX_RE = re.compile(
    r"^[ \t\f]*[\(（<〈＜\[]\s*((?:별\s*표|부\s*표)\s*(?:\d+(?:\s*[-－]\s*\d+)?)?|별\s*첨)\s*[\)）>〉＞\]][^\n]{0,40}$",
    re.M,
)
# 인용 법령 부록: "[부록] 약관에서 인용된 법령내용" (목차 줄은 뒤에 쪽번호가 붙어 안 걸린다)
LAW_APPENDIX_RE = re.compile(
    r"^[ \t\f]*(?:\[\s*부\s*록\s*\][^\n]{0,30}법\s*령[^\n]{0,10}"
    r"|[^\n]{0,3}아래\s*법령은\s*약관에서\s*인용된\s*법령[^\n]*)$",
    re.M,
)
# 조 안의 소제목: "[질병입원형 보상내용]" 처럼 대괄호로 감싼 짧은 줄
SUBBLOCK_RE = re.compile(r"^[ \t\f]*\[\s*([^\]\n]{2,30}?)\s*\][ \t]*$", re.M)
# 별표 제목 줄이 아니라 본문 문장 속 참조("(별표5) …과 같이 계산합니다")인지 가르는 꼬리
APPENDIX_REF_TAIL_RE = re.compile(r"(다|니다)\.?\s*$|과\s*같이|에\s*따라|에서\s*정한|참\s*조")
TITLE_LOOKBACK = 6  # 제1조(목적) 위로 구획 제목을 찾아볼 줄 수
TABLE_CHUNK_CHARS = 1000  # 별표 표를 자르는 크기 (조각마다 표 제목을 다시 붙이므로 한도보다 작게)
MAX_ARTICLE_JUMP = 5  # 삭제된 조 등으로 번호가 건너뛰는 최대 폭


@dataclass
class Section:
    """통합약관의 구획 하나 (주계약 · 특약 · 별표 · 부록 · 앞부분)."""

    kind: str  # 앞부분 / 주계약 / 특약 / 별표 / 부록
    name: str  # 화면·키에 쓰는 이름 (예: 무배당11대피부질환입원특약)
    start: int
    end: int
    parent: str | None = None  # 별표가 딸린 구획 이름


def _squash(s: str) -> str:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    return re.sub(r"\s+", "", s)


def _is_real_start(text: str, m: re.Match) -> bool:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    # 목차라면 다음 줄이 곧바로 "제2조(…)" 같은 조 제목이거나 쪽번호다.
    # 본문이라면 다음 조 제목이 나오기 전에 "…니다." 로 끝나는 문장이 있다.
    rest = text[m.end() : m.end() + 400]
    nxt = re.search(r"^[ \t\f]*제\s*\d+\s*조", rest, re.M)
    # 문장 끝이 줄바꿈으로 나뉜 경우("체결됩니 / 다.")도 잡도록 공백을 지우고 본다
    return "니다." in _squash(rest[: nxt.start()] if nxt else rest)


def _section_title(text: str, at: int, floor: int) -> tuple[str | None, int]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    # 제1조(목적) 위쪽 줄들(제1관 줄 제외)을 모아 구획 제목으로 쓴다. 문장 끝(…니다.)을 만나면 멈춘다.
    lines, pos = [], at
    while len(lines) < TITLE_LOOKBACK and pos > floor:
        prev = text.rfind("\n", floor, pos - 1)
        line_start = prev + 1 if prev >= floor else floor
        line = text[line_start:pos].strip()
        pos = line_start
        # 빈 줄, 관 제목, "※ …보증합니다." 같은 안내 줄은 건너뛴다
        if not line or re.match(r"^제\s*\d+\s*관|^※", line):
            continue
        # 본문 문장의 끝(…다. / …다), 목록 항목(1. ① (주)), 목차 줄(점선·쪽번호)을 만나면 멈춘다
        if re.search(r"다\.?$|\.$", line) or re.match(r"(\d+\.|[①-⑳]|\(주\))", line):
            note_at = _note_start(text, floor, line_start)
            if note_at is not None:  # 여러 줄짜리 "※ …보증합니다." 안내문이면 통째로 건너뛴다
                pos = note_at
                continue
            break
        if re.search(r"\.{3,}|·{3,}|…\s*\d+$", line):
            break
        lines.insert(0, line)
    if not lines:
        return None, at
    title = _squash("".join(lines))
    title = re.sub(r"[￡£]", "", title)
    # 제목 줄이 두 번 찍힌 판("…특약 약관 / …특약 약관")은 "약관"으로 나눈 첫 조각만 쓴다
    title = next((p for p in re.split(r"약관", title) if p), title)
    return title, pos


def _note_start(text: str, floor: int, pos: int) -> int | None:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    # pos 바로 위 3줄 안에 "※"로 시작하는 줄이 (다른 문장 끝 없이) 있으면 그 줄의 시작 위치
    for _ in range(3):
        if pos <= floor:
            return None
        prev = text.rfind("\n", floor, pos - 1)
        start = prev + 1 if prev >= floor else floor
        line = text[start:pos].strip()
        pos = start
        if line.startswith("※"):
            return start
        if re.search(r"다\.?$", line):
            return None
    return None


def find_sections(text: str) -> list[Section]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    starts = [m for m in SECTION_START_RE.finditer(text) if _is_real_start(text, m)]
    if len(starts) < 2:  # 특약이 붙지 않은 단일 약관·규정 → 기존 방식
        return []

    heads: list[tuple[int, str, str]] = []  # (구획 시작 위치, 종류, 이름)
    floor = 0
    for i, m in enumerate(starts):
        window_from = max(floor, m.start() - 800)
        sentences = list(RIDER_SENTENCE_RE.finditer(text, window_from, m.start()))
        title, title_pos = _section_title(text, m.start(), floor)
        if sentences:
            kind, name = "특약", _clean_name(sentences[-1].group(1))
            begin = min(sentences[-1].start(), title_pos)
        elif i == 0 or (title and ("주계약" in title or "특약" not in title)):
            # 제목에 "특약"이 없으면 주계약의 다른 형(일반형 플러스 등)이다
            kind, name, begin = "주계약", f"주계약{_main_variant(title)}", title_pos
        else:
            kind, name, begin = "특약", _clean_name(title) if title else f"특약{i}", title_pos
        heads.append((begin, kind, name))
        floor = m.end()

    law_at = [m.start() for m in LAW_APPENDIX_RE.finditer(text) if m.start() > heads[0][0]]
    sections: list[Section] = []
    if heads[0][0] > 0:
        sections.append(Section("앞부분", "앞부분", 0, heads[0][0]))
    used: dict[str, int] = {}
    for i, (begin, kind, name) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(text)
        laws = [a for a in law_at if begin < a < end]
        if laws:
            end_body = laws[0]
        else:
            end_body = end
        used[name] = used.get(name, 0) + 1
        if used[name] > 1:
            name = f"{name}#{used[name]}"
        sections.extend(_with_appendices(text, kind, name, begin, end_body))
        if laws:
            sections.append(Section("부록", f"{name}:인용법령", laws[0], end, parent=name))
    return _mark_duplicate_copies(text, sections)


def _mark_duplicate_copies(text: str, sections: list[Section]) -> list[Section]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    # 같은 특약 약관이 한 PDF에 여러 벌 실린 경우(실손 비급여 특약 3벌, 암진단보험료환급특약 1형·2형):
    # 이름이 "…#2"이고 본문(공백 제외)이 첫 벌과 글자 하나까지 같을 때만 "제외"로 표시해 청크를 만들지 않는다.
    # 한 글자라도 다르면 다른 특약으로 보고 남긴다 (1형·2형의 실제 차이를 잃지 않게).
    bodies = {
        s.name: _squash(text[s.start : s.end]) for s in sections if s.kind in ("주계약", "특약")
    }
    dropped: set[str] = set()
    for s in sections:
        m = re.match(r"(.+)#\d+$", s.name)
        if s.kind not in ("주계약", "특약") or not m or m.group(1) not in bodies:
            continue
        if bodies[m.group(1)] == bodies[s.name]:
            dropped.add(s.name)
    for s in sections:
        if s.name in dropped or s.parent in dropped:
            s.kind = "제외"
    return sections


def _main_variant(title: str | None) -> str:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    # "주계약(일반형,집중보장형)" 처럼 주계약이 여러 개인 상품은 괄호 안 이름으로 구분한다
    m = re.search(r"주계약(\([^)]{1,40}\))", title or "")
    if m:
        return m.group(1)
    # "…종신보험Ⅱ(보증비용부과형)일반형플러스,집중보장형플러스" → "(일반형플러스,집중보장형플러스)"
    tail = re.search(r"\)([^()]{2,40}형[^()]{0,20})$", title or "")
    return f"({tail.group(1)})" if tail else ""


def _clean_name(name: str) -> str:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    name = _squash(name)
    name = name.rsplit("`", 1)[-1]  # 앞 표의 꼬리("…와동일`")가 붙은 경우
    half = len(name) // 2
    if len(name) % 2 == 0 and name[:half] == name[half:]:  # 제목이 두 번 찍힌 경우
        name = name[:half]
    # "…_2107비급여실손의료비특약(갱신형)의질병비급여형,상해비급여형,3대비급여형보장종목"
    # → "비급여실손의료비특약(갱신형)[질병비급여형,상해비급여형,3대비급여형]"
    m = re.match(r"(?:.*_\d{4})?(.+?특약(?:\([^)]*\))?)의(.+?)보장종목$", name)
    if m:
        name = f"{m.group(1)}[{m.group(2)}]"
    return name


def _with_appendices(text: str, kind: str, name: str, begin: int, end: int) -> list[Section]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    marks = [
        mk
        for mk in APPENDIX_RE.finditer(text, begin, end)
        if not APPENDIX_REF_TAIL_RE.search(text[mk.end(1) : mk.end()])
    ]
    if not marks:
        return [Section(kind, name, begin, end)]
    out = [Section(kind, name, begin, marks[0].start())]
    seen: dict[str, int] = {}
    for j, mk in enumerate(marks):
        a_end = marks[j + 1].start() if j + 1 < len(marks) else end
        label = _squash(mk.group(1))
        seen[label] = seen.get(label, 0) + 1
        if seen[label] > 1:
            label = f"{label}#{seen[label]}"
        out.append(Section("별표", f"{name}:{label}", mk.start(), a_end, parent=name))
    return out


def _split_structured(text: str, page_starts: list[int], sections: list[Section]) -> list[Chunk]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    chunks: list[Chunk] = []
    used: dict[str, int] = {}

    def add(key, part, chapter, article_no, title, para_no, heading, start, end, piece, sec):
        """TODO(재홍): 무엇을 왜 하는가 한 문장"""
        used[key] = used.get(key, 0) + 1
        if used[key] > 1:  # 구조 인식이 놓친 중복 → 키를 살리되 표시(~N)를 남겨 검수에서 센다
            key = f"{key}~{used[key]}"
        c = _make(
            len(chunks),
            key,
            part,
            chapter,
            article_no,
            title,
            para_no,
            heading,
            start,
            end,
            piece,
            page_starts,
        )
        c.section = sec
        # 길어서 여러 조각으로 잘린 경우 조각마다 실제 위치의 쪽 번호를 쓴다 (조각 가운데 글을 원문에서 찾는다)
        mid = piece[len(piece) // 2 : len(piece) // 2 + 30]
        loc = text.find(mid, start, end + 1) if len(mid) == 30 else -1
        if loc >= 0:
            c.page = _page_of(loc, page_starts)
        chunks.append(c)

    for sec in sections:
        if sec.kind == "제외":
            continue
        body = text[sec.start : sec.end]
        if sec.kind in ("앞부분", "별표", "부록"):
            heading = sec.name if sec.kind != "앞부분" else "앞부분(목차·유의사항)"
            # 별표 표는 조각마다 표 제목 줄을 다시 붙여, 조각만 검색돼도 무슨 표인지 알 수 있게 한다
            pieces = _split_table(body.strip(), repeat_title=sec.kind == "별표")
            for j, piece in enumerate(pieces):
                add(
                    f"{sec.name}#{j + 1}",
                    sec.kind,
                    None,
                    None,
                    None,
                    None,
                    heading,
                    sec.start,
                    sec.end,
                    piece,
                    sec.parent or sec.name,
                )
            continue

        chapters = [
            (sec.start + m.start(), f"{_norm_article(m.group(1))} {m.group(2).strip()}".strip())
            for m in CHAPTER_RE.finditer(body)
        ]
        # 조 번호가 앞으로, 조금씩만 가는 것만 조 제목으로 인정한다.
        # 본문·표 안의 법령 인용 줄("제42조(요양기관)")은 번호가 크게 뛰므로 거른다.
        articles, last = [], (0, 0)
        for m in STRUCT_ARTICLE_RE.finditer(body):
            num = (int(m.group(2)), int(m.group(3) or 0))
            # 구획의 첫 조는 번호와 상관없이 받는다 (주피형·종피형 특약은 제21조(목적)처럼 이어서 시작)
            if not articles or (num > last and num[0] <= last[0] + MAX_ARTICLE_JUMP):
                articles.append(m)
                last = num
        if not articles:
            for j, piece in enumerate(_split_long(body.strip())):
                add(
                    f"{sec.name}#{j + 1}",
                    sec.kind,
                    None,
                    None,
                    None,
                    None,
                    sec.name,
                    sec.start,
                    sec.end,
                    piece,
                    sec.name,
                )
            continue
        head = body[: articles[0].start()].strip()
        if head:
            for j, piece in enumerate(_split_long(head)):
                add(
                    f"{sec.name}|머리" + (f"#{j + 1}" if j else ""),
                    sec.kind,
                    None,
                    None,
                    None,
                    None,
                    f"{sec.name} 머리말",
                    sec.start,
                    sec.start + articles[0].start(),
                    piece,
                    sec.name,
                )

        for i, m in enumerate(articles):
            a_start = m.start()
            a_end = articles[i + 1].start() if i + 1 < len(articles) else len(body)
            for at, _ in chapters:  # 다음 관 제목이 사이에 있으면 거기서 끊는다
                if sec.start + a_start < at < sec.start + a_end:
                    a_end = at - sec.start
            art_body = body[a_start:a_end].strip()
            article_no = _norm_article(m.group(1))
            title = re.sub(r"\s+", " ", m.group(4)).strip()
            chapter = _last_before(chapters, sec.start + a_start)
            base = f"{sec.name}|{article_no}"
            # 출처에 어느 주계약·특약의 조항인지 보이도록 화면 제목 앞에 구획 이름을 붙인다
            base_heading = f"{sec.name} {article_no}({title})"
            para_marks = list(PARAGRAPH_RE.finditer(art_body))
            # 조 하나가 한도 안이면 통째로 한 청크 (조 전체 맥락이 한 번에 검색된다)
            if len(art_body) <= MAX_CHUNK_CHARS or len(para_marks) < 2:
                for j, piece in enumerate(_split_long(art_body)):
                    add(
                        base + (f"#{j + 1}" if j else ""),
                        sec.kind,
                        chapter,
                        article_no,
                        title,
                        None,
                        base_heading,
                        sec.start + a_start,
                        sec.start + a_end,
                        piece,
                        sec.name,
                    )
                continue
            p_head = art_body[: para_marks[0].start()].strip()
            # 실손 제3조처럼 "[질병입원형 보상내용]" 소제목마다 ①부터 다시 시작하는 조가 있다
            subs = [(m.start(), _squash(m.group(1))) for m in SUBBLOCK_RE.finditer(art_body)]
            for k, pm in enumerate(para_marks):
                p_end = para_marks[k + 1].start() if k + 1 < len(para_marks) else len(art_body)
                para_no = pm.group(1)
                para_text = art_body[pm.start() : p_end].strip()
                full = f"{p_head}\n{para_text}" if p_head else para_text
                idx = CIRCLED.index(para_no) + 1
                sub = _last_before(subs, pm.start())
                p_key = f"{base}[{sub}]-{idx}" if sub else f"{base}-{idx}"
                p_heading = (
                    f"{base_heading} [{sub}] {para_no}항" if sub else f"{base_heading} {para_no}항"
                )
                for j, piece in enumerate(_split_long(full)):
                    add(
                        p_key + (f"#{j + 1}" if j else ""),
                        sec.kind,
                        chapter,
                        article_no,
                        title,
                        para_no,
                        p_heading,
                        sec.start + a_start + pm.start(),
                        sec.start + a_start + p_end,
                        piece,
                        sec.name,
                    )
    return chunks


def _split_table(body: str, repeat_title: bool) -> list[str]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    lines = [ln for ln in body.split("\n")]
    title = ""
    if repeat_title:
        firsts = [ln.strip() for ln in lines if ln.strip()][:2]
        title = " ".join(firsts)[:120]
    pieces, current = [], ""
    for ln in lines:
        if current and len(current) + len(ln) + 1 > TABLE_CHUNK_CHARS:
            pieces.append(current.strip())
            current = f"{title} (이어서)\n" if title else ""
        current += ln + "\n"
    if current.strip():
        pieces.append(current.strip())
    return [q for p in pieces for q in _hard_cap(p)]


def embedding_text(doc_title: str, version_label: str | None, c: Chunk) -> str:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    # 임베딩할 글 앞에 위치 정보를 붙인다: 같은 "제3조"라도 상품·판·특약이 다르면 다른 벡터가 되게
    head = f"[{doc_title}" + (f" {version_label}" if version_label else "") + "]"
    if c.section and c.section not in c.heading:
        head += f" [{c.section}]"
    if c.chapter:
        head += f" [{c.chapter}]"
    return f"{head} {c.heading}\n{c.text}"


def _split_flat(text: str, page_starts: list[int]) -> list[Chunk]:
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
    return [q for p in pieces for q in _hard_cap(p)]


def _hard_cap(piece: str) -> list[str]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    # 문단 경계로 잘라도 한도를 넘는 덩어리(줄바꿈뿐인 표 등)는 줄 단위로, 그래도 넘는 줄은 글자 수로 자른다
    if len(piece) <= MAX_CHUNK_CHARS:
        return [piece]
    out, current = [], ""
    for ln in piece.split("\n"):
        while len(ln) > MAX_CHUNK_CHARS:
            if current:
                out.append(current.strip())
                current = ""
            out.append(ln[:MAX_CHUNK_CHARS])
            ln = ln[MAX_CHUNK_CHARS:]
        if current and len(current) + len(ln) + 1 > MAX_CHUNK_CHARS:
            out.append(current.strip())
            current = ""
        current += ln + "\n"
    if current.strip():
        out.append(current.strip())
    return [o for o in out if o]


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
    return max(1, bisect.bisect_right(page_starts, pos))


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
