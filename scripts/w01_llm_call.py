# 1주차 — LLM 호출 스크립트
#
# 요구사항
#   1. LiteLLM으로 클라우드 모델 1개 호출 (모델명은 insure_copilot.config.settings에서)  ← 구현됨
#   2. (선택) Ollama 로컬 모델 1개 호출                                              ← [직접 작성]
#   3. 출력: 모델명 · 프롬프트 · 응답 · 응답 시간(초)                                 ← [직접 작성]
#   4. 추가: 입력/출력 토큰 수(resp.usage), 비용(litellm.completion_cost)             ← [직접 작성]
#
# 실행: uv run python scripts/w01_llm_call.py

import litellm

from insure_copilot.config import settings

PROMPT = "실손의료보험에서 '실손'은 무엇을 뜻하나요? 한 문장으로 답해 주세요."


def call_cloud_model(prompt: str, model: str = settings.default_model) -> str:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    resp = litellm.completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        num_retries=3,
    )
    return resp.choices[0].message.content


if __name__ == "__main__":
    print(call_cloud_model(PROMPT))
