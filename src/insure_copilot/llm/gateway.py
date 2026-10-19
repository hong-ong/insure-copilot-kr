"""LLM·임베딩 호출의 단일 관문. 모델 교체·fallback·토큰·비용 기록을 여기서만 한다."""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import litellm

from insure_copilot.config import settings

litellm.drop_params = True
if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
    litellm.success_callback = ["langfuse"]
    litellm.failure_callback = ["langfuse"]


@dataclass
class LLMResult:
    """한 번의 LLM 호출 결과와 운영 지표(토큰·비용·지연)를 함께 담는다."""

    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def add(self, other: LLMResult) -> None:
        """TODO(재홍): 무엇을 왜 하는가 한 문장"""
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens
        self.cost_usd += other.cost_usd
        self.latency_ms += other.latency_ms


def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    # 무료 티어라 실제 청구는 0원이지만, 상용 전환 시 비용을 보여주기 위해 환산 단가로 계산한다.
    return (
        prompt_tokens * settings.price_input_per_m + completion_tokens * settings.price_output_per_m
    ) / 1_000_000


def complete(
    messages: list[dict[str, Any]],
    *,
    temperature: float = 0.1,
    max_tokens: int = 1200,
    json_mode: bool = False,
    model: str | None = None,
    trace_name: str = "chat",
    trace_id: str | None = None,
) -> LLMResult:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    models = [model or settings.default_model, settings.fallback_model]
    last_error: Exception | None = None
    trace_id = trace_id or uuid.uuid4().hex
    for m in dict.fromkeys(models):  # 중복 제거, 순서 유지
        started = time.perf_counter()
        try:
            kwargs: dict[str, Any] = {
                "model": m,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "num_retries": 2,
                "metadata": {"trace_name": trace_name, "trace_id": trace_id},
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            resp = litellm.completion(**kwargs)
        except Exception as e:  # 주 모델 실패 → 대체 모델로
            last_error = e
            continue
        usage = getattr(resp, "usage", None)
        pt = int(getattr(usage, "prompt_tokens", 0) or 0)
        ct = int(getattr(usage, "completion_tokens", 0) or 0)
        return LLMResult(
            text=resp.choices[0].message.content or "",
            model=m,
            prompt_tokens=pt,
            completion_tokens=ct,
            cost_usd=estimate_cost(pt, ct),
            latency_ms=int((time.perf_counter() - started) * 1000),
            trace_id=trace_id,
        )
    raise RuntimeError(f"모든 모델 호출 실패: {last_error}")


def complete_json(messages: list[dict[str, Any]], **kwargs: Any) -> tuple[dict, LLMResult]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    result = complete(messages, json_mode=True, **kwargs)
    return parse_json(result.text), result


def parse_json(text: str) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}


def embed(texts: list[str], *, task: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    vectors: list[list[float]] = []
    batch = 50
    for i in range(0, len(texts), batch):
        resp = litellm.embedding(
            model=settings.embedding_model,
            input=texts[i : i + batch],
            dimensions=settings.embedding_dim,
            task_type=task,
            num_retries=3,
        )
        vectors.extend(item["embedding"] for item in resp.data)
    return vectors


def embed_query(text: str) -> list[float]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    return embed([text], task="RETRIEVAL_QUERY")[0]
