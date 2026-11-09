#!/usr/bin/env bash
# AI 백엔드를 Hugging Face Spaces(Docker)에 배포한다.
# Spaces 저장소는 README.md 맨 위에 설정(YAML)이 있어야 해서, 필요한 파일만 임시 폴더에 모아 따로 push 한다.
#
# 사용법: bash scripts/deploy_hf.sh <HF 사용자명>/<space 이름>
#   예)   bash scripts/deploy_hf.sh hong-ong/gaon-ax-api
# 사전 준비: huggingface.co에서 Docker Space 생성, Settings → Variables and secrets 에 .env 값 등록,
#           git 인증(HF 액세스 토큰)을 해 둔다.
set -euo pipefail

SPACE="${1:?사용법: bash scripts/deploy_hf.sh <user>/<space>}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

git clone --depth 1 "https://huggingface.co/spaces/${SPACE}" "$TMP/space"
cd "$TMP/space"
find . -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +

cp -r "$ROOT/src" "$ROOT/pyproject.toml" "$ROOT/uv.lock" "$ROOT/Dockerfile" "$ROOT/.dockerignore" .
mkdir -p data && cp -r "$ROOT/data/samples" data/
cat > README.md <<'EOF'
---
title: 가온생명 AX 어시스턴트 API
emoji: 🏦
colorFrom: indigo
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

가온생명 AX 어시스턴트의 AI 백엔드(FastAPI). 소스: https://github.com/hong-ong/insure-copilot-kr
EOF

git add -A
git commit -m "deploy: $(git -C "$ROOT" rev-parse --short HEAD)" || echo "변경 없음"
git push
echo "배포 요청 완료 → https://huggingface.co/spaces/${SPACE} 에서 빌드 로그를 확인하세요."
