"""글자를 제대로 못 뽑은 PDF를 페이지 이미지로 바꿔 Gemini 비전으로 다시 읽는다 (OCR).

OCR은 페이지마다 LLM을 부르므로 비싸다 → 파일 10MB 제한 + 최대 페이지 수(OCR_MAX_PAGES)로 막는다.
"""

from __future__ import annotations

import base64

from insure_copilot.llm.gateway import LLMResult, complete

OCR_PROMPT = (
    "이 이미지는 한국어 보험 약관·규정·사내 문서의 한 페이지입니다. "
    "보이는 글자를 빠짐없이 그대로 옮겨 적으세요. 요약·해석·설명을 덧붙이지 마세요. "
    "조항 번호(제1조, ①)와 줄바꿈을 유지하고, 표는 '|'로 칸을 구분한 줄로 적으세요."
)


def ocr_pages(images: list[bytes]) -> tuple[list[str], LLMResult]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    total = LLMResult(text="", model="")
    pages: list[str] = []
    for png in images:
        b64 = base64.b64encode(png).decode()
        result = complete(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": OCR_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    ],
                }
            ],
            temperature=0,
            max_tokens=4000,
            trace_name="ocr",
        )
        pages.append(result.text)
        total.model = result.model
        total.add(result)
    return pages, total
