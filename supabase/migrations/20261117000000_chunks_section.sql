-- 통합약관의 구획(주계약 · 특약 이름 · 별표 · 부록)을 청크마다 저장한다.
-- 같은 "제3조"라도 특약이 다르면 다른 조항이므로, 검색 결과를 특약 단위로 거르거나 묶을 때 쓴다.
-- (ADR-0004, 0부 준비 ②-4)
alter table public.chunks add column if not exists section text;
create index if not exists chunks_document_section_idx on public.chunks (document_id, section);
