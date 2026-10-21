"""API 종단 간 점검: 데모 계정(익명 로그인)으로 핵심 시나리오를 실제 Supabase·Gemini에 대고 돌린다.

실행: (백엔드를 :8000에 띄운 뒤) uv run python scripts/e2e_api.py
결과는 사람이 읽고 판단한다 — 정답 채점은 골든셋 평가(3~4주차)의 몫이다.
"""

from __future__ import annotations

import sys
import time

import httpx

from insure_copilot.config import settings

API = "http://localhost:8000"


def demo_login(role: str) -> str:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    r = httpx.post(
        f"{settings.supabase_url}/auth/v1/signup",
        headers={"apikey": settings.supabase_anon_key},
        json={"data": {}},
        timeout=30,
    )
    r.raise_for_status()
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    httpx.post(f"{API}/demo/start", headers=h, json={"role": role}, timeout=30).raise_for_status()
    httpx.post(f"{API}/notice/agree", headers=h, timeout=30).raise_for_status()
    return token


def ask(token: str, q: str, conv: str | None = None) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    t = time.time()
    r = httpx.post(
        f"{API}/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": q, "conversation_id": conv},
        timeout=120,
    )
    if r.status_code != 200:
        print(f"\n❌ {q}\n   HTTP {r.status_code} {r.text[:200]}")
        return {}
    d = r.json()
    m = d["message"]
    print(f"\n🙋 {q}  [{m['route']}{' · 거절' if m['refused'] else ''}] {time.time() - t:.1f}s")
    print("   " + m["content"].replace("\n", "\n   ")[:700])
    for c in m["citations"]:
        print(f"   📎 [{c['rank']}] {c['label']}{' (구버전)' if c['is_expired'] else ''}")
    return d


def main() -> int:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    print("== 설계사 데모")
    agent = demo_login("agent")
    d = ask(agent, "실비로 도수치료 몇 번까지 돼?")
    ask(agent, "작년에 가입한 고객은?", d.get("conversation_id"))
    ask(
        agent,
        "이 고객 보험금 받을 수 있어? 허리 디스크로 도수치료 30회 받았대. 홍길동 010-1234-5678",
    )
    ask(agent, "내 13회차 유지율 알려줘")
    ask(agent, "도수치료 한도 줄인 이유가 뭐였지?")
    ask(
        agent, "보험금 청구 처리 FAQ에서 민원 유형 알려줘"
    )  # 지급팀 전용 문서 → 설계사에게 안 보여야 함

    print("\n== 법무팀 데모")
    legal = demo_login("legal")
    ask(legal, "보험금 청구 처리 FAQ에서 민원 유형 알려줘")  # 본사는 팀 문서도 보임
    ask(legal, "지난 분기 지점별 불완전판매비율 보여줘")

    me = httpx.get(f"{API}/me", headers={"Authorization": f"Bearer {agent}"}, timeout=30).json()
    print(f"\n데모 사용량: {me['demo']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
