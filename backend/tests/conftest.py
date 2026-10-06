"""测试夹具：每个用例使用临时 SQLite，不碰 data/checkins.db。"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    import db

    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    from main import app

    with TestClient(app) as test_client:
        yield test_client
