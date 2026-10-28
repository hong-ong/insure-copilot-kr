#!/usr/bin/env bash
# SessionStart 훅: 세션 시작 시 원격 변경을 받아 온다 (git pull --rebase --autostash).
# 어떤 경우에도 exit 0 — 세션 시작을 막지 않는다. stdout은 Claude 컨텍스트에 들어간다.

export GIT_TERMINAL_PROMPT=0   # 자격 증명 프롬프트로 멈추지 않게
export GCM_INTERACTIVE=never   # Windows Git Credential Manager 창 띄우지 않기
export GIT_EDITOR=true

cd "$(dirname "$0")" 2>/dev/null && cd "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || {
  echo "[sync-pull] 저장소를 찾지 못해 건너뜀"
  exit 0
}

# 지난 세션 종료 시 push가 실패했으면 여기서 알린다 (SessionEnd 출력은 사용자에게 안 보이므로)
last_err="$(git rev-parse --git-path claude-sync-push-error)"
if [ -f "$last_err" ]; then
  echo "[sync-pull] 지난 세션 종료 시 자동 push 실패:"
  cat "$last_err"
  rm -f "$last_err"
fi

git_dir="$(git rev-parse --git-dir)"
if [ -d "$git_dir/rebase-merge" ] || [ -d "$git_dir/rebase-apply" ]; then
  echo "[sync-pull] 진행 중인 rebase가 있어 pull 건너뜀, git status 확인 필요"
  exit 0
fi

if ! git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
  echo "[sync-pull] 현재 브랜치에 upstream이 없어 pull 건너뜀"
  exit 0
fi

if out="$(git pull --rebase --autostash 2>&1)"; then
  echo "[sync-pull] $(git rev-parse --abbrev-ref HEAD): $(printf '%s\n' "$out" | tail -n 1)"
else
  if [ -d "$git_dir/rebase-merge" ] || [ -d "$git_dir/rebase-apply" ]; then
    git rebase --abort >/dev/null 2>&1
  fi
  echo "충돌로 pull 실패, git status 확인 필요"
  printf '%s\n' "$out" | tail -n 5
fi
exit 0
