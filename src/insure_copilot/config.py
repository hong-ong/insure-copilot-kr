"""환경변수(.env)에서 설정을 읽어 한 곳에서 관리한다."""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _split(value: str | None) -> list[str]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    return [v.strip() for v in (value or "").split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    """모델 이름 등 실행 설정을 코드 곳곳에 하드코딩하지 않기 위해 모아 둔다."""

    # LLM (LiteLLM 모델 문자열)
    default_model: str = os.getenv("DEFAULT_MODEL", "gemini/gemini-flash-lite-latest")
    fallback_model: str = os.getenv("FALLBACK_MODEL", "gemini/gemini-2.5-flash")
    llm_timeout: float = float(os.getenv("LLM_TIMEOUT", "25"))  # 초. 넘으면 대체 모델로
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "gemini/gemini-embedding-001")
    embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "768"))
    # Gemini 생각(thinking) 수준. 비우면 모델 기본값(생각을 많이 해서 느리고 토큰을 더 씀)
    reasoning_effort: str = os.getenv("REASONING_EFFORT", "low")
    local_model: str = os.getenv("LOCAL_MODEL", "ollama/qwen2.5:7b")
    # 무료 티어여도 "상용 전환 시 비용"을 보여주기 위해 환산 단가를 둔다 (USD / 1M tokens)
    price_input_per_m: float = float(os.getenv("PRICE_INPUT_PER_M", "0.30"))
    price_output_per_m: float = float(os.getenv("PRICE_OUTPUT_PER_M", "2.50"))

    # Supabase
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY", "")
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    # 서비스 정책
    max_upload_bytes: int = 10 * 1024 * 1024
    approve_threshold: float = float(os.getenv("PARSE_APPROVE_THRESHOLD", "0.90"))
    hold_threshold: float = float(os.getenv("PARSE_HOLD_THRESHOLD", "0.70"))
    ocr_max_pages: int = int(os.getenv("OCR_MAX_PAGES", "30"))
    demo_daily_limit: int = int(os.getenv("DEMO_DAILY_LIMIT", "10"))
    top_k: int = int(os.getenv("TOP_K", "6"))
    cors_origins: list[str] = field(
        default_factory=lambda: _split(os.getenv("CORS_ORIGINS", "http://localhost:3000"))
    )

    # 정보계
    mart_path: str = os.getenv("MART_PATH", "data/processed/mart.duckdb")

    law_api_oc: str | None = os.getenv("LAW_API_OC") or None


settings = Settings()
