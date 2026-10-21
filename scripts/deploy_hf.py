"""AI 백엔드를 Hugging Face Spaces(Docker)에 배포한다 — git 없이 API로.

실행: uv run --with huggingface_hub python scripts/deploy_hf.py [space 이름]
필요: .env 의 HF_TOKEN(Write 권한) 과 서버용 키들. 비밀값은 Space Secrets로 등록되어 코드·로그에 남지 않는다.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

from dotenv import dotenv_values
from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[1]
SECRETS = ["GEMINI_API_KEY", "SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY"]
VARIABLES = [
    "DEFAULT_MODEL",
    "FALLBACK_MODEL",
    "EMBEDDING_MODEL",
    "EMBEDDING_DIM",
    "REASONING_EFFORT",
    "PRICE_INPUT_PER_M",
    "PRICE_OUTPUT_PER_M",
    "DEMO_DAILY_LIMIT",
    "PARSE_APPROVE_THRESHOLD",
    "PARSE_HOLD_THRESHOLD",
    "OCR_MAX_PAGES",
    "CORS_ORIGINS",
]
README = """---
title: Gaon AX Assistant API
emoji: 🏦
colorFrom: indigo
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

가온생명 AX 어시스턴트의 AI 백엔드(FastAPI). 소스: https://github.com/hong-ong/insure-copilot-kr
"""


def main() -> int:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    name = sys.argv[1] if len(sys.argv) > 1 else "gaon-ax-api"
    env = dotenv_values(ROOT / ".env")
    api = HfApi(token=env["HF_TOKEN"])
    repo_id = f"{api.whoami()['name']}/{name}"
    api.create_repo(repo_id, repo_type="space", space_sdk="docker", exist_ok=True)

    for key in SECRETS:
        api.add_space_secret(repo_id, key, env[key])
    for key in VARIABLES:
        if env.get(key):
            api.add_space_variable(repo_id, key, env[key])

    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp)
        for item in ["src", "pyproject.toml", "uv.lock", "Dockerfile", ".dockerignore"]:
            src = ROOT / item
            (shutil.copytree if src.is_dir() else shutil.copy2)(src, stage / item)
        shutil.copytree(ROOT / "data" / "samples", stage / "data" / "samples")
        (stage / "README.md").write_text(README, encoding="utf-8")
        api.upload_folder(
            repo_id=repo_id,
            repo_type="space",
            folder_path=stage,
            commit_message="deploy",
            ignore_patterns=["**/__pycache__/**", "*.pyc"],
            delete_patterns=["src/**"],
        )
    sub = repo_id.replace("/", "-").replace("_", "-").lower()
    print(f"Space: https://huggingface.co/spaces/{repo_id}")
    print(f"API:   https://{sub}.hf.space/health")
    return 0


if __name__ == "__main__":
    sys.exit(main())
