"""파서·품질 판정·조항 분할·마스킹 회귀 테스트 (네트워크·LLM 없이 돈다)."""

import io
import zipfile
from pathlib import Path

import docx

from insure_copilot.ingest import clauses, formats, masking, quality

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples"


def test_normal_korean_is_approved():
    text = (SAMPLES / "gaon-silson-rider-2026-04.md").read_text(encoding="utf-8")
    report = quality.hangul_recognition(text)
    assert report.score >= 0.9
    assert quality.judge(report.score, 0.9, 0.7) == "approved"


def test_replacement_chars_are_rejected():
    text = "보험금 �ýý� ��� 지급 ÃÃÃ " * 50
    report = quality.hangul_recognition(text)
    assert report.score < 0.7


def test_valid_but_repeated_syllables_are_rejected():
    # 글꼴 매핑이 깨진 PDF: 정상 한글 음절이지만 같은 글자만 반복된다
    text = "사사사사 사사 사사사 사사사사사 사사 " * 100
    report = quality.hangul_recognition(text)
    assert report.diversity < 0.2
    assert quality.judge(report.score, 0.9, 0.7) == "rejected"


def test_clause_keys_match_across_versions():
    old = clauses.split_clauses(
        (SAMPLES / "gaon-silson-rider-2025-07.md").read_text(encoding="utf-8"), [0]
    )
    new = clauses.split_clauses(
        (SAMPLES / "gaon-silson-rider-2026-04.md").read_text(encoding="utf-8"), [0]
    )
    old_keys, new_keys = {c.chunk_key for c in old}, {c.chunk_key for c in new}
    assert "제4조-2" in old_keys and "제4조-2" in new_keys
    assert new_keys - old_keys == {"제2조-5", "제9조-3"}  # 신설 조항
    c = next(c for c in new if c.chunk_key == "제4조-2")
    assert c.article_title == "보상하는 손해" and c.paragraph_no == "②"
    assert "300만원" in c.text


def test_masking_personal_and_health_info():
    r = masking.mask(
        "홍길동 고객은 작년에 당뇨 진단을 받았고 연락처는 010-1234-5678, 주민번호 900101-1234567"
    )
    assert "010-1234-5678" not in r.text and "900101-1234567" not in r.text
    assert "당뇨" not in r.text
    assert r.counts["휴대전화"] == 1


def test_disease_codes_kept_in_terms():
    assert "C00" in masking.mask("C00~C97 악성신생물", disease_codes=False).text
    assert "C34.9" not in masking.mask("진단코드 C34.9", disease_codes=True).text


def test_extract_hwpx_and_docx():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("mimetype", "application/hwp+zip")
        z.writestr(
            "Contents/section0.xml",
            '<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" '
            'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">'
            "<hp:p><hp:run><hp:t>제1조(목적) 이 약관은</hp:t></hp:run></hp:p></hs:sec>",
        )
    ex = formats.extract("a.hwpx", buf.getvalue())
    assert ex.file_format == "hwpx" and "제1조(목적)" in ex.text

    d = docx.Document()
    d.add_paragraph("제2조(정의) 보험금이란")
    out = io.BytesIO()
    d.save(out)
    ex = formats.extract("b.docx", out.getvalue())
    assert ex.file_format == "docx" and "보험금" in ex.text


def test_terms_and_dates_are_not_over_masked():
    terms = (
        "① 회사는 피보험자가 질병 또는 상해로 의료기관에서 입원하여 치료를 받은 경우 보상합니다."
    )
    assert masking.mask(terms, disease_codes=False, person_health=False).text == terms
    assert (
        "회사는 피보험자가" in masking.mask(terms).text
    )  # 사용자 입력 모드에서도 '회사'는 이름이 아니다
    assert "2026-10-12" in masking.mask("회의일 2026-10-12, 계좌 110-123-456789").text
    assert "110-123-456789" not in masking.mask("계좌 110-123-456789").text
