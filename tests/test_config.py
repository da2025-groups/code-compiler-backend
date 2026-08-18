import os
import pytest
from unittest.mock import patch


def test_settings_loads_from_env():
    """Settings reads all required env vars."""
    env = {
        "SECRET_KEY": "test-secret",
        "ADMIN_EMAIL": "admin@test.com",
        "ADMIN_PASSWORD": "testpass",
        "PISTON_URL": "http://localhost:2000",
        "DATABASE_URL": "sqlite:///./test.db",
    }
    with patch.dict(os.environ, env, clear=False):
        # Re-import to pick up patched env
        import importlib
        import app.config as cfg_module
        importlib.reload(cfg_module)
        s = cfg_module.Settings()
        assert s.secret_key == "test-secret"
        assert s.admin_email == "admin@test.com"
        assert s.admin_password == "testpass"
        assert s.piston_url == "http://localhost:2000"
        assert s.database_url == "sqlite:///./test.db"
