#!/usr/bin/env bash
# AI 백엔드(FastAPI)를 Vercel Python 함수로 배포한다 (프로젝트 gaon-ax-api → https://gaon-ax-api.vercel.app).
# 필요한 파일만 임시 폴더에 모은다: 백엔드 코드 + deploy/vercel-api(진입점·설정) + requirements.txt.
# requirements.txt 는 uv.lock 에서 뽑되 Kiwi(모델 100MB+)와 로컬 개발용 서버 부가 패키지는 뺀다 (함수 용량 한도 대비).
#
# 사용법: bash scripts/deploy_api_vercel.sh
# 사전 준비: .env 에 VERCEL_TOKEN, Vercel 프로젝트 환경변수 등록 (docs/setup.md 5장)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
UV="${UV:-C:/develop/_tools/uv/uv.exe}"
export PATH="/c/develop/_tools/node:$PATH"
TOKEN="$(grep -E '^VERCEL_TOKEN=' "$ROOT/.env" | cut -d= -f2- | tr -d '\r')"

cp -r "$ROOT/deploy/vercel-api/." "$TMP/"
cp -r "$ROOT/src/insure_copilot" "$TMP/insure_copilot"
find "$TMP" -name __pycache__ -type d -prune -exec rm -rf {} +
(cd "$ROOT" && "$UV" export --no-dev --no-hashes --no-emit-project --frozen) \
  | grep -vE '^\s*#|^\s*$|^(kiwipiepy|uvloop|watchfiles|httptools|colorama|tzdata)' > "$TMP/requirements.txt"

cd "$TMP"
npx --yes vercel@latest link --yes --project gaon-ax-api --token "$TOKEN" > /dev/null
npx --yes vercel@latest deploy --prod --yes --token "$TOKEN"
