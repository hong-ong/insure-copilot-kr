"""답변 속 인용 번호 정리·후속 질문 검색어 (LLM·DB 없이)."""

from insure_copilot.agent import rag
from insure_copilot.retrieval.search import Hit


def _hit(i: int) -> Hit:
    return Hit(
        id=f"c{i}",
        document_id="d",
        chunk_key=f"k{i}",
        heading=f"h{i}",
        part="본문",
        page=1,
        text="t",
        title="T",
        doc_type="terms",
        version_label=None,
        version_group_id="g",
        effective_from=None,
        effective_to=None,
        doc_status="active",
        similarity=0.9,
    )


def test_grouped_citations_are_renumbered(monkeypatch):
    hits = [_hit(i) for i in range(1, 6)]
    monkeypatch.setattr(rag, "search", lambda *a, **k: hits)
    monkeypatch.setattr(rag, "previous_versions", lambda *a, **k: [])
    answer = {
        "answer": "한도는 300만원입니다 [S3, S5]. 소견서가 필요합니다 [S3]. 예외는 [2].",
        "citations": ["S3"],
    }
    monkeypatch.setattr(rag, "complete_json", lambda *a, **k: (answer, None))
    out = rag.answer_rag(None, "q", [], None)
    assert [h.id for h in out.citations] == ["c3", "c5", "c2"]
    assert out.content == "한도는 300만원입니다 [1][2]. 소견서가 필요합니다 [1]. 예외는 [3]."


def test_short_followup_uses_previous_question():
    history = [
        {"role": "user", "content": "실비로 도수치료 몇 번까지 돼?"},
        {"role": "assistant", "content": "..."},
    ]
    assert (
        rag.search_query("작년에 가입한 고객은?", history)
        == "실비로 도수치료 몇 번까지 돼? 작년에 가입한 고객은?"
    )
    assert rag.search_query(
        "비중증 비급여 자기부담금은 2026년 4월 개정 이후 얼마로 바뀌었나요?", history
    ).startswith("비중증")
