"""
설정(Config) 모듈 단위 테스트
- Pydantic V2 model_validator 동작 검증
- DATABASE_URL 조합 로직
- REDIS_URL 조합 로직
"""

import os
from unittest.mock import patch


class TestSettingsAssembly:
    """Settings URL 조합 로직 테스트"""

    def test_database_url_from_parts(self):
        """POSTGRES_* 개별 변수로 DATABASE_URL 조합"""
        env = {
            "SECRET_KEY": "test-secret",
            "POSTGRES_SERVER": "localhost",
            "POSTGRES_USER": "myuser",
            "POSTGRES_PASSWORD": "mypass",
            "POSTGRES_DB": "mydb",
            "POSTGRES_PORT": "5432",
        }
        with patch.dict(os.environ, env, clear=True):
            # Settings를 새로 임포트하기 위해 모듈 리로드
            import importlib

            import app.core.config as config_module

            importlib.reload(config_module)
            settings = config_module.Settings()

            assert settings.DATABASE_URL == "postgresql+asyncpg://myuser:mypass@localhost:5432/mydb"

    def test_database_url_from_direct(self):
        """DATABASE_URL 직접 설정 (Railway 방식)"""
        env = {
            "SECRET_KEY": "test-secret",
            "DATABASE_URL": "postgres://user:pass@host:5432/db",
        }
        with patch.dict(os.environ, env, clear=True):
            import importlib

            import app.core.config as config_module

            importlib.reload(config_module)
            settings = config_module.Settings()

            # postgres:// -> postgresql+asyncpg:// 변환 확인
            assert "postgresql+asyncpg://" in settings.DATABASE_URL

    def test_redis_url_from_parts(self):
        """REDIS_* 개별 변수로 REDIS_URL 조합"""
        env = {
            "SECRET_KEY": "test-secret",
            "REDIS_HOST": "redis-host",
            "REDIS_PORT": "6379",
        }
        with patch.dict(os.environ, env, clear=True):
            import importlib

            import app.core.config as config_module

            importlib.reload(config_module)
            settings = config_module.Settings()

            assert settings.REDIS_URL == "redis://redis-host:6379"

    def test_redis_url_from_parts_with_password(self):
        """비밀번호가 있는 REDIS_URL 조합"""
        env = {
            "SECRET_KEY": "test-secret",
            "REDIS_HOST": "redis-host",
            "REDIS_PORT": "6379",
            "REDIS_PASSWORD": "myredispass",
        }
        with patch.dict(os.environ, env, clear=True):
            import importlib

            import app.core.config as config_module

            importlib.reload(config_module)
            settings = config_module.Settings()

            assert settings.REDIS_URL == "redis://:myredispass@redis-host:6379"

    def test_redis_url_direct(self):
        """REDIS_URL 직접 설정"""
        env = {
            "SECRET_KEY": "test-secret",
            "REDIS_URL": "redis://custom-redis:6380/0",
        }
        with patch.dict(os.environ, env, clear=True):
            import importlib

            import app.core.config as config_module

            importlib.reload(config_module)
            settings = config_module.Settings()

            assert settings.REDIS_URL == "redis://custom-redis:6380/0"

    def test_database_url_none_when_not_configured(self):
        """DATABASE_URL 미설정 시 None"""
        env = {
            "SECRET_KEY": "test-secret",
        }
        with patch.dict(os.environ, env, clear=True):
            import importlib

            import app.core.config as config_module

            importlib.reload(config_module)
            settings = config_module.Settings()

            assert settings.DATABASE_URL is None

    def test_extra_env_vars_ignored(self):
        """정의되지 않은 환경변수는 무시 (extra='ignore')"""
        env = {
            "SECRET_KEY": "test-secret",
            "UNKNOWN_VARIABLE": "some-value",
        }
        with patch.dict(os.environ, env, clear=True):
            import importlib

            import app.core.config as config_module

            importlib.reload(config_module)
            # 예외 없이 Settings 생성 가능
            settings = config_module.Settings()
            assert settings.SECRET_KEY == "test-secret"
