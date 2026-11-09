"""Supabase 접속. 두 종류의 클라이언트를 구분해서 쓴다.

- service(): 서비스 키(모든 권한). 파이프라인 쓰기·관리 집계처럼 서버가 책임지는 작업에만 쓴다.
- as_user(token): 로그인 사용자의 토큰으로 접속 → RLS가 적용된다. 검색·조회는 이걸 쓴다.
"""

from __future__ import annotations

from functools import lru_cache

from supabase import Client, ClientOptions, create_client

from insure_copilot.config import settings


class NotConfigured(RuntimeError):
    """Supabase 환경변수가 비어 있을 때."""


def _check() -> None:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    if not (settings.supabase_url and settings.supabase_anon_key and settings.supabase_service_key):
        raise NotConfigured(
            "SUPABASE_URL / SUPABASE_ANON_KEY / SUPABASE_SERVICE_ROLE_KEY 를 .env에 넣어 주세요."
        )


@lru_cache(maxsize=1)
def service() -> Client:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    _check()
    return create_client(settings.supabase_url, settings.supabase_service_key)


def as_user(access_token: str) -> Client:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    _check()
    return create_client(
        settings.supabase_url,
        settings.supabase_anon_key,
        options=ClientOptions(headers={"Authorization": f"Bearer {access_token}"}),
    )
