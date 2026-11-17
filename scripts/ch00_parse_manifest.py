# 0부 준비 — data/manifest.csv의 교보 약관을 서비스 파서로 파싱해 E: processed 구역에 저장한다.
#
# 원본(raw)은 읽기만 한다. 결과는 판마다 두 파일 + 요약표 하나:
#   <slug>_<sale_from>.md            페이지를 \f로 이은 본문 (서비스 documents.markdown과 같은 형식)
#   <slug>_<sale_from>.chunks.jsonl  조항 청크 (서비스 chunks 테이블과 같은 필드, 임베딩 없음)
#   parse_report.csv                 판별 인식률·조항 인식 상태
# LLM·임베딩 호출 없음. 서비스 업로드의 10MB 제한은 적용하지 않는다(로컬 적재 전용).
#
# 실행: uv run python scripts/ch00_parse_manifest.py [--out E:\insure-copilot-data\kyobo\processed]

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from insure_copilot.config import settings
from insure_copilot.ingest import clauses, formats, masking, quality
from insure_copilot.ingest.pipeline import PAGE_BREAK

ROOT = Path(__file__).resolve().parents[1]
SLUGS = {"실손": "silson3", "암보험": "cancer_d2408", "종신": "hanaro_whole2"}


def slug_of(product: str) -> str:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    return next(v for k, v in SLUGS.items() if k in product)


def parse_one(row: dict, out: Path) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    data = Path(row["raw_path"]).read_bytes()
    extracted = formats.extract(row["file_name"], data)
    report = quality.hangul_recognition(extracted.text)
    verdict = quality.judge(report.score, settings.approve_threshold, settings.hold_threshold)
    # 서비스 파이프라인과 같은 마스킹 (약관은 질병코드·건강정보 마스킹을 끈다)
    pages = [
        masking.mask(p, disease_codes=False, person_health=False).text for p in extracted.pages
    ]

    text = PAGE_BREAK.join(pages)
    page_starts, pos = [], 0
    for p in pages:
        page_starts.append(pos)
        pos += len(p) + len(PAGE_BREAK)
    chunks = clauses.split_clauses(text, page_starts)
    for c in chunks:
        c.text = c.text.replace(PAGE_BREAK, "\n")

    stem = f"{slug_of(row['product'])}_{row['sale_from']}"
    (out / f"{stem}.md").write_text(text, encoding="utf-8")
    with open(out / f"{stem}.chunks.jsonl", "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")

    sections = clauses.find_sections(text)
    kinds = Counter(s.kind for s in sections)
    riders = [s.name for s in sections if s.kind == "특약"]
    with open(out / f"{stem}.sections.txt", "w", encoding="utf-8") as f:
        for s in sections:
            f.write(f"{s.kind}\t{s.name}\tp{clauses._page_of(s.start, page_starts)}\n")
    rider_sentences = len(clauses.RIDER_SENTENCE_RE.findall(text))
    lens = [len(c.text) for c in chunks] or [0]
    return {
        "stem": stem,
        "product": row["product"],
        "sale_from": row["sale_from"],
        "embed": row["embed"],
        "pages": len(pages),
        "chars": sum(len(p) for p in pages),
        "hangul_score": f"{report.score:.3f}",
        "verdict": verdict,
        "chunks": len(chunks),
        "space_ratio": f"{text.count(' ') / max(len(text), 1):.3f}",
        "main": kinds["주계약"],
        "riders": len(riders),
        "rider_sentences": rider_sentences,
        "unique_riders": len(set(riders)),
        "appendices": kinds["별표"],
        "law_appendix": kinds["부록"],
        "articles": len({(c.section, c.article_no) for c in chunks if c.article_no}),
        "dup_chunk_keys": sum(1 for c in chunks if re.search(r"~\d+$", c.chunk_key)),
        "avg_chunk_chars": sum(lens) // len(lens),
        "max_chunk_chars": max(lens),
    }


def main() -> None:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(ROOT / "data" / "manifest.csv"))
    ap.add_argument("--out", default=r"E:\insure-copilot-data\kyobo\processed")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rows = list(csv.DictReader(open(args.manifest, encoding="utf-8")))
    results = []
    for row in rows:
        r = parse_one(row, out)
        results.append(r)
        print(
            f"{r['stem']}: {r['pages']}쪽 · 청크 {r['chunks']} · 인식률 {r['hangul_score']}",
            flush=True,
        )
    with open(out / "parse_report.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)


if __name__ == "__main__":
    main()
