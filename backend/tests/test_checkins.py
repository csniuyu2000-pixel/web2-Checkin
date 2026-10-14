"""打卡接口：正常打卡、10 分钟内重复、非法输入。"""
from tests.helpers import auth_header, login_student


def test_normal_checkin_logged_in(client):
    token = login_student(client)
    response = client.post(
        "/api/checkins",
        json={"name": "学生甲", "location": "教学楼"},
        headers=auth_header(token),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "学生甲"
    assert body["location"] == "教学楼"
    assert body["user_id"] is not None
    assert body["created_at"]


def test_duplicate_checkin_within_10_minutes(client):
    token = login_student(client)
    first = client.post(
        "/api/checkins",
        json={"name": "学生甲", "location": "一号楼"},
        headers=auth_header(token),
    )
    assert first.status_code == 200, first.text

    second = client.post(
        "/api/checkins",
        json={"name": "学生甲", "location": "二号楼"},
        headers=auth_header(token),
    )
    assert second.status_code == 409
    assert "10 minutes" in second.json()["detail"]


def test_checkin_rejects_short_name(client):
    token = login_student(client)
    response = client.post(
        "/api/checkins",
        json={"name": "张", "location": "校园"},
        headers=auth_header(token),
    )
    assert response.status_code == 422


def test_checkin_rejects_empty_location(client):
    token = login_student(client)
    response = client.post(
        "/api/checkins",
        json={"name": "张三", "location": "   "},
        headers=auth_header(token),
    )
    assert response.status_code == 422


def test_checkin_rejects_too_long_name(client):
    token = login_student(client)
    response = client.post(
        "/api/checkins",
        json={"name": "啊" * 21, "location": "校园"},
        headers=auth_header(token),
    )
    assert response.status_code == 422
