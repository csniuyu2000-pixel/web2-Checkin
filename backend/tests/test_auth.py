"""登录、注册与查询权限：无 token、错误密码、学生看不到别人。"""
from tests.helpers import auth_header, login


def test_login_success(client):
    response = client.post(
        "/api/login", json={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "admin"
    assert body["token"]


def test_login_wrong_password(client):
    response = client.post(
        "/api/login", json={"username": "admin", "password": "wrongpass"}
    )
    assert response.status_code == 401


def test_login_empty_username(client):
    response = client.post(
        "/api/login", json={"username": "  ", "password": "admin123"}
    )
    assert response.status_code == 422


def test_register_invalid_short_password(client):
    response = client.post(
        "/api/register", json={"username": "newbie", "password": "123"}
    )
    assert response.status_code == 422


def test_query_without_token(client):
    response = client.get("/api/checkins")
    assert response.status_code == 401


def test_query_with_invalid_token(client):
    response = client.get(
        "/api/checkins", headers=auth_header("not-a-valid-token")
    )
    assert response.status_code == 401


def test_student_cannot_see_admin_checkin(client):
    admin_token = login(client, "admin", "admin123")
    student_token = login(client, "student", "student123")

    created = client.post(
        "/api/checkins",
        json={"name": "管理员", "location": "办公楼"},
        headers=auth_header(admin_token),
    )
    assert created.status_code == 200
    admin_checkin_id = created.json()["id"]

    student_list = client.get("/api/checkins", headers=auth_header(student_token))
    assert student_list.status_code == 200
    ids = {item["id"] for item in student_list.json()}
    assert admin_checkin_id not in ids


def test_admin_can_see_all_checkins(client):
    admin_token = login(client, "admin", "admin123")
    student_token = login(client, "student", "student123")

    student_created = client.post(
        "/api/checkins",
        json={"name": "学生甲", "location": "宿舍"},
        headers=auth_header(student_token),
    )
    assert student_created.status_code == 200
    student_id = student_created.json()["id"]

    admin_list = client.get("/api/checkins", headers=auth_header(admin_token))
    assert admin_list.status_code == 200
    ids = {item["id"] for item in admin_list.json()}
    assert student_id in ids
