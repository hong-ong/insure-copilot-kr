"""벡터 검색. 로그인 사용자의 토큰으로 match_chunks를 부르므로 권한 밖 문서는 애초에 나오지 않는다 (RLS)."""

from __future__ import annotations

from dataclasses import dataclass

from supabase import Client

from insure_copilot.config import settings
from insure_copilot.llm.gateway import embed_query


@dataclass
class Hit:
    """검색된 청크 하나 + 출처 표시에 필요한 문서 정보."""

    id: str
    document_id: str
    chunk_key: str
    heading: str
    part: str
    page: int | None
    text: str
    title: str
    doc_type: str
    version_label: str | None
    version_group_id: str
    effective_from: str | None
    effective_to: str | None
    doc_status: str
    similarity: float

    @property
    def is_expired(self) -> bool:
        """TODO(재홍): 무엇을 왜 하는가 한 문장"""
        return self.doc_status == "expired"

    @property
    def label(self) -> str:
        """TODO(재홍): 무엇을 왜 하는가 한 문장"""
        parts = [self.title, self.heading]
        if self.version_label:
            parts.append(self.version_label)
        return " · ".join(p for p in parts if p)


def search(
    client: Client, query: str, k: int | None = None, include_expired: bool = False
) -> list[Hit]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    vector = embed_query(query)
    rows = (
        client.rpc(
            "match_chunks",
            {
                "query_embedding": vector,
                "match_count": k or settings.top_k,
                "include_expired": include_expired,
            },
        )
        .execute()
        .data
        or []
    )
    return [Hit(**{k_: r.get(k_) for k_ in Hit.__dataclass_fields__}) for r in rows]


def previous_versions(client: Client, hits: list[Hit]) -> list[Hit]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    # 검색된 조항에 '이전 판'이 있으면 같은 조항 키의 구버전 본문을 함께 가져온다.
    # → "2026.04 이전 가입자는 구 약관 적용" 같은 안내를 답변에 넣기 위해.
    active = [h for h in hits if not h.is_expired]
    if not active:
        return []
    group_ids = list({h.version_group_id for h in active})
    docs = (
        client.table("documents")
        .select(
            "id, title, version_label, version_group_id, effective_from, effective_to, status, doc_type"
        )
        .in_("version_group_id", group_ids)
        .eq("status", "expired")
        .execute()
        .data
        or []
    )
    if not docs:
        return []
    by_id = {d["id"]: d for d in docs}
    keys = list({h.chunk_key for h in active})
    rows = (
        client.table("chunks")
        .select("id, document_id, chunk_key, heading, part, page, text")
        .in_("document_id", list(by_id))
        .in_("chunk_key", keys)
        .execute()
        .data
        or []
    )
    out = []
    for r in rows:
        d = by_id[r["document_id"]]
        out.append(
            Hit(
                id=r["id"],
                document_id=r["document_id"],
                chunk_key=r["chunk_key"],
                heading=r["heading"],
                part=r["part"],
                page=r["page"],
                text=r["text"],
                title=d["title"],
                doc_type=d["doc_type"],
                version_label=d["version_label"],
                version_group_id=d["version_group_id"],
                effective_from=d["effective_from"],
                effective_to=d["effective_to"],
                doc_status="expired",
                similarity=0.0,
            )
        )
    return out
