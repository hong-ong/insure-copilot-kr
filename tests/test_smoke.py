"""패키지가 import되고 설정이 읽히는지 확인하는 최소 테스트."""

from insure_copilot import __version__
from insure_copilot.config import settings


def test_package_imports():
    assert __version__


def test_settings_have_default_model():
    assert settings.default_model
