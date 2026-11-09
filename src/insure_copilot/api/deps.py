"""요청마다 로그인 토큰을 확인하고 사용자 프로필을 붙인다."""

from __future__ import annotations

import hashlib

from fastapi import Depends, Header, HTTPException

from insure_copilot.agent.orchestrator import UserContext
from insure_copilot.store import db


def _default_profile(user) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    meta = getattr(user, "user_metadata", None) or {}
    name = meta.get("full_name") or meta.get("name") or (user.email or "").split("@")[0] or "사용자"
    return {
        "id": user.id,
        "display_name": name,
        "team": "sales",
        "role": "agent",
        "is_demo": False,
        "onboarded": False,
    }


def agent_code_for(user_id: str) -> str:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    # 가입한 설계사를 가상 마트의 설계사 한 명(A0001~A0300)에 고정 연결 → "내 실적" 지표 질문이 동작하게 한다
    n = int(hashlib.sha256(user_id.encode()).hexdigest(), 16) % 300 + 1
    return f"A{n:04d}"


def current_user(authorization: str = Header(default="")) -> UserContext:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "로그인이 필요합니다.")
    token = authorization.split(" ", 1)[1]
    try:
        user = db.service().auth.get_user(token).user
    except Exception as e:
        raise HTTPException(401, "로그인이 만료되었습니다. 다시 로그인해 주세요.") from e
    if user is None:
        raise HTTPException(401, "로그인이 필요합니다.")

    sb = db.service()
    rows = sb.table("profiles").select("*").eq("id", user.id).execute().data
    if rows:
        profile = rows[0]
    else:
        profile = _default_profile(user)
        profile["agent_code"] = agent_code_for(user.id)
        profile["is_demo"] = bool(getattr(user, "is_anonymous", False))
        profile = sb.table("profiles").insert(profile).execute().data[0]
    profile["is_anonymous"] = bool(getattr(user, "is_anonymous", False))
    return UserContext(user_id=user.id, access_token=token, profile=profile)


def require_member(ctx: UserContext = Depends(current_user)) -> UserContext:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    if ctx.profile.get("is_demo"):
        raise HTTPException(
            403, "데모 계정에서는 사용할 수 없는 기능이에요. 가입하면 모든 기능을 쓸 수 있습니다."
        )
    return ctx


def require_role(*roles: str):
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""

    def checker(ctx: UserContext = Depends(current_user)) -> UserContext:
        """TODO(재홍): 무엇을 왜 하는가 한 문장"""
        if ctx.profile.get("role") not in roles:
            raise HTTPException(403, "이 화면을 볼 권한이 없습니다.")
        return ctx

    return checker


def require_role_write(*roles: str):
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""

    def checker(ctx: UserContext = Depends(current_user)) -> UserContext:
        """TODO(재홍): 무엇을 왜 하는가 한 문장"""
        if ctx.profile.get("role") not in roles:
            raise HTTPException(403, "권한이 없습니다.")
        if ctx.profile.get("is_demo"):
            raise HTTPException(403, "데모 계정은 읽기 전용이에요.")
        return ctx

    return checker
