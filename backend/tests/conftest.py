"""测试夹具：每个用例使用临时 SQLite，不碰 data/checkins.db。"""
import pytest
from fastapi.testclient import TestClient

# 测试用固定凭据（与生产 .env 无关；须在 import main 之前注入）
TEST_TOKEN_SECRET = "pytest-token-secret-key-at-least-32-chars"
TEST_ADMIN_PASSWORD = "pytest-admin-pass"
TEST_STUDENT_PASSWORD = "pytest-student-pass"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_SECRET", TEST_TOKEN_SECRET)
    monkeypatch.setenv("DEMO_ADMIN_PASSWORD", TEST_ADMIN_PASSWORD)
    monkeypatch.setenv("DEMO_STUDENT_PASSWORD", TEST_STUDENT_PASSWORD)
    monkeypatch.setenv("CORS_ORIGINS", "http://testserver")

    import db

    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    from main import app

    with TestClient(app) as test_client:
        yield test_client
