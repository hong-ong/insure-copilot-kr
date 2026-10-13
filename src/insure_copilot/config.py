"""환경변수(.env)에서 설정을 읽어 한 곳에서 관리한다."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """모델 이름 등 실행 설정을 코드 곳곳에 하드코딩하지 않기 위해 모아 둔다."""

    default_model: str = os.getenv("DEFAULT_MODEL", "gemini/gemini-2.5-flash")
    local_model: str = os.getenv("LOCAL_MODEL", "ollama/qwen2.5:7b")
    law_api_oc: str | None = os.getenv("LAW_API_OC") or None


settings = Settings()
