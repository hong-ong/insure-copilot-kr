#!/usr/bin/env bash
# SessionEnd 훅: 변경을 자동 커밋하고 pull --rebase 후 push 한다. 강제 push는 하지 않는다.
# 실패 사유는 stderr로 출력하고, 다음 세션 시작 때 sync-pull.sh가 보여 주도록 .git 안에 남긴다.

export GIT_TERMINAL_PROMPT=0
export GCM_INTERACTIVE=never
export GIT_EDITOR=true

cd "$(dirname "$0")" 2>/dev/null && cd "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || {
  echo "[sync-push] 저장소를 찾지 못해 건너뜀" >&2
  exit 0
}

git_dir="$(git rev-parse --git-dir)"
err_file="$(git rev-parse --git-path claude-sync-push-error)"

fail() {
  local msg="[sync-push] $1"
  echo "$msg" >&2
  [ -n "$2" ] && printf '%s\n' "$2" | tail -n 5 >&2
  { echo "$(date '+%Y-%m-%d %H:%M') $msg"; [ -n "$2" ] && printf '%s\n' "$2" | tail -n 5; } >"$err_file"
  exit 1
}

in_rebase() { [ -d "$git_dir/rebase-merge" ] || [ -d "$git_dir/rebase-apply" ]; }

in_rebase && fail "진행 중인 rebase가 있어 자동 동기화 건너뜀, git status 확인 필요"

branch="$(git symbolic-ref --short -q HEAD)" || fail "detached HEAD 상태라 건너뜀"

if [ -n "$(git status --porcelain)" ]; then
  host="$(hostname 2>/dev/null | cut -d. -f1)"
  git add -A || fail "git add 실패"
  out="$(git commit -q -m "auto: ${host:-unknown} 세션 종료 $(date '+%Y-%m-%d %H:%M')" 2>&1)" \
    || fail "자동 커밋 실패" "$out"
fi

git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1 \
  || fail "$branch 브랜치에 upstream이 없어 push 건너뜀 (커밋은 로컬에 있음)"

if ! out="$(git pull --rebase --autostash 2>&1)"; then
  in_rebase && git rebase --abort >/dev/null 2>&1
  fail "충돌로 pull 실패, push 안 함 (커밋은 로컬에 있음). git status 확인 필요" "$out"
fi

out="$(git push 2>&1)" || fail "push 실패 (커밋은 로컬에 있음)" "$out"

rm -f "$err_file"
echo "[sync-push] $branch: $(printf '%s\n' "$out" | tail -n 1)"
exit 0
