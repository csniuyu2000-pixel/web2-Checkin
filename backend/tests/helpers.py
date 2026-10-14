"""测试辅助函数。"""
from fastapi.testclient import TestClient

from tests.conftest import TEST_ADMIN_PASSWORD, TEST_STUDENT_PASSWORD


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def login(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/api/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]


def login_admin(client: TestClient) -> str:
    return login(client, "admin", TEST_ADMIN_PASSWORD)


def login_student(client: TestClient) -> str:
    return login(client, "student", TEST_STUDENT_PASSWORD)
