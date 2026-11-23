# 0부 준비 ②-5 — 파싱 결과 검수. ch00_parse_manifest.py를 먼저 돌린 뒤 실행한다.
#
# 1) 특약 대조: 판마다 앞부분(목차)의 특약 목록 ↔ 구조 인식이 찾은 특약 구획을 맞춰 본다
#    → reviews/ch00_section_check.csv (판·목차 이름·찾은 이름·일치 여부)
# 2) 원문 대조 표본 20개: 청크를 무작위(고정 시드)로 뽑아, 서비스 파서와 다른 방식(PyMuPDF 기본 추출)으로
#    같은 쪽을 다시 읽고 청크 글이 그 쪽에 실제로 있는지, 조 번호가 맞는지 확인한다
#    → reviews/parsing_review.csv
# LLM·임베딩 호출 없음. 원본은 읽기만 한다.
#
# 실행: uv run python scripts/ch00_review.py [--processed E:\insure-copilot-data\kyobo\processed]

from __future__ import annotations

import argparse
import csv
import difflib
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLUGS = {"실손": "silson3", "암보험": "cancer_d2408", "종신": "hanaro_whole2"}
SAMPLE_SIZE = 20
SEED = 20261117


def norm_name(s: str) -> str:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    s = re.sub(r"\.{2,}.*$|·{2,}.*$|\s\d+$", "", s)  # 목차 점선·쪽번호
    s = s.replace("(무)", "무배당").replace("약관", "")
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"\[[^\]]*\]|\((주피형|종피형|주피형,종피형)\)", "", s)
    s = s.replace("New무배당", "무배당New")  # 목차 "New(무)…" ↔ 본문 "무배당 New…"
    return s


def toc_riders(front: str) -> list[str]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    names = []
    for line in front.split("\n"):
        line = line.strip()
        if len(line) > 90 or "특약" not in line:
            continue
        # 목차 항목 모양: "(무)…특약…" / "New(무)…" / "무배당 …특약 약관 ……… 196" / "…서비스특약"
        if re.match(r"^(New)?\s*\(무\)|^무배당|^New\s*무배당", line) or re.search(
            r"특약\s*약관\s*.*\.{3,}\s*\d+$|^[가-힣\s]*서비스특약$|^[가-힣\s]*재개특약$", line
        ):
            n = norm_name(line)
            if n and n not in names:
                names.append(n)
    return names


def match_names(toc: list[str], found: list[str]) -> list[tuple[str, str, float]]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    # 글자 순서가 조금 다른 이름("…특약(갱신형)Ⅱ" ↔ "…특약Ⅱ(갱신형)")도 맞도록 유사도로 1:1 짝을 짓는다
    pairs = sorted(
        ((difflib.SequenceMatcher(None, t, f).ratio(), t, f) for t in toc for f in found),
        reverse=True,
    )
    used_t, used_f, out = set(), set(), []
    for r, t, f in pairs:
        if r < 0.8 or t in used_t or f in used_f:
            continue
        used_t.add(t)
        used_f.add(f)
        out.append((t, f, r))
    out += [(t, "", 0.0) for t in toc if t not in used_t]
    out += [("", f, 0.0) for f in found if f not in used_f]
    return out


def main() -> None:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    import pymupdf

    ap = argparse.ArgumentParser()
    ap.add_argument("--processed", default=r"E:\insure-copilot-data\kyobo\processed")
    args = ap.parse_args()
    proc = Path(args.processed)
    rows = list(csv.DictReader(open(ROOT / "data" / "manifest.csv", encoding="utf-8")))

    # 1) 특약 대조
    check, summary = [], []
    for row in rows:
        stem = f"{next(v for k, v in SLUGS.items() if k in row['product'])}_{row['sale_from']}"
        text = (proc / f"{stem}.md").read_text(encoding="utf-8")
        secs = [
            ln.rstrip("\n").split("\t")
            for ln in open(proc / f"{stem}.sections.txt", encoding="utf-8")
        ]
        first_page = int(next(s for s in secs if s[0] != "앞부분")[2][1:])
        front = "\f".join(text.split("\f")[: first_page - 1])
        toc = toc_riders(front)
        found = [norm_name(s[1]) for s in secs if s[0] == "특약"]
        excluded = [norm_name(s[1]) for s in secs if s[0] == "제외" and ":" not in s[1]]
        pairs = match_names(toc, found)
        for t, f, r in pairs:
            check.append(
                {
                    "stem": stem,
                    "toc_name": t,
                    "found_name": f,
                    "similarity": f"{r:.2f}",
                    "result": "일치" if t and f else ("목차에만" if t else "찾은 것에만"),
                }
            )
        summary.append(
            (
                stem,
                len(toc),
                len(found),
                len(excluded),
                sum(1 for t, f, _ in pairs if t and f),
                sum(1 for t, f, _ in pairs if t and not f),
                sum(1 for t, f, _ in pairs if f and not t),
            )
        )
    with open(ROOT / "reviews" / "ch00_section_check.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(check[0].keys()))
        w.writeheader()
        w.writerows(check)
    print("stem\t목차특약\t찾은특약\t제외(중복)\t일치\t목차에만\t찾은것에만")
    for s in summary:
        print("\t".join(map(str, s)))

    # 2) 원문 대조 표본 20개 (임베딩 대상 판에서만, 주계약·특약 조항 위주 + 별표 일부)
    rng = random.Random(SEED)
    pool = []
    for row in rows:
        if row["embed"] != "true":
            continue
        stem = f"{next(v for k, v in SLUGS.items() if k in row['product'])}_{row['sale_from']}"
        for ln in open(proc / f"{stem}.chunks.jsonl", encoding="utf-8"):
            c = json.loads(ln)
            if c["part"] in ("주계약", "특약", "별표"):
                pool.append((row, c))
    samples = rng.sample(pool, SAMPLE_SIZE)
    out = []
    docs: dict[str, pymupdf.Document] = {}
    for i, (row, c) in enumerate(samples, 1):
        doc = docs.setdefault(row["raw_path"], pymupdf.open(row["raw_path"]))
        page = c["page"] or 1

        def pages_text(lo: int, hi: int, doc=doc) -> str:
            """TODO(재홍): 무엇을 왜 하는가 한 문장"""
            return "".join(doc[p].get_text() for p in range(max(lo, 0), min(hi, doc.page_count)))

        body = c["text"]
        # 청크 앞에 덧붙인 글(항 청크의 조 제목 줄, 별표 조각의 "표 제목 (이어서)" 줄)은 빼고 대조한다
        core = body
        if body.split("\n", 1)[0].endswith("(이어서)"):
            core = body.split("\n", 1)[1]
        elif c["paragraph_no"] and c["paragraph_no"] in body:
            core = body[body.index(c["paragraph_no"]) :]
        sq = re.sub(r"\s+", "", core)
        head, mid, tail = sq[:30], sq[len(sq) // 2 : len(sq) // 2 + 30], sq[-30:]
        window = re.sub(r"\s+", "", pages_text(page - 3, page + 2))
        here = re.sub(r"\s+", "", pages_text(page - 2, page + 1))  # 표시한 쪽 ± 1쪽
        text_ok = head in window and mid in window and tail in window
        page_ok = mid in here
        art_ok = (not c["article_no"]) or (
            c["article_no"] in re.sub(r"\s+", "", pages_text(page - 30, page + 1) + body[:80])
        )
        errors = []
        if not text_ok:
            errors.append("본문 불일치")
        if not page_ok:
            errors.append("쪽 번호 불일치")
        if not art_ok:
            errors.append("조 번호 불일치")
        raw = pages_text(page - 1, page + 1)
        out.append(
            {
                "sample_id": f"S{i:02d}",
                "document": f"{row['display_name']} · {row['sale_from']} 판",
                "pdf_page": page,
                "clause": c["heading"],
                "original_excerpt": raw[raw.find(core[:6]) if core[:6] in raw else 0 :][
                    :80
                ].replace("\n", " "),
                "parsed_excerpt": core[:80].replace("\n", " "),
                "match": "Y" if not errors else "N",
                "error_type": ", ".join(errors),
                "note": f"자동 대조(PyMuPDF 기본 추출, 공백 무시) · 구획={c['section']} · {len(body)}자",
            }
        )
    with open(ROOT / "reviews" / "parsing_review.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print(f"표본 {len(out)}개 중 일치 {sum(1 for o in out if o['match'] == 'Y')}개")


if __name__ == "__main__":
    main()
