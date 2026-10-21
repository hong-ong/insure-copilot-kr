# 2주차 — Docling으로 실손의료보험 표준약관 PDF를 마크다운으로 변환한다.
#
# 입력: data/raw/silson_standard.pdf  (보험업감독업무시행세칙 별표15, 2026-08-28 발령, p.204-313 실손 부분 — data/SOURCES.md)
# 출력: data/processed/silson_standard.md
# 실행: uv run python src/parsing/parse_pdf.py

from pathlib import Path

from docling.document_converter import DocumentConverter

src = Path("data/raw/silson_standard.pdf")
result = DocumentConverter().convert(src)
md = result.document.export_to_markdown()
Path("data/processed/silson_standard.md").write_text(md, encoding="utf-8")
