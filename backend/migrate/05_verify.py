"""步骤 G：对比 SQLite（真实子集）与 MySQL，行数 + 抽样，防止丢数据。"""
import json
import random
import sys
from getpass import getpass
from pathlib import Path

try:
    import pymysql
except ImportError as exc:
    raise SystemExit("请先安装：pip install pymysql") from exc

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from db import get_connection  # noqa: E402

HOST = "127.0.0.1"
PORT = 3306
USER = "root"
DATABASE = "riqian"
SAMPLE = 20


def main():
    password = getpass(f"MySQL 密码（用户 {USER}@{HOST}）: ")

    sqlite_conn = get_connection()
    try:
        sqlite_users = sqlite_conn.execute(
            "SELECT id, username, password_hash, role FROM users ORDER BY id"
        ).fetchall()
        sqlite_checkins = sqlite_conn.execute(
            """
            SELECT id, name, location, created_at, user_id
            FROM checkins
            WHERE user_id IS NOT NULL
            ORDER BY id
            """
        ).fetchall()
    finally:
        sqlite_conn.close()

    mysql_conn = pymysql.connect(
        host=HOST,
        port=PORT,
        user=USER,
        password=password,
        database=DATABASE,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        with mysql_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM users")
            mysql_users_n = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) AS n FROM checkins")
            mysql_checkins_n = cur.fetchone()["n"]

            cur.execute("SELECT id, username, password_hash, role FROM users ORDER BY id")
            mysql_users = cur.fetchall()
            cur.execute(
                "SELECT id, name, location, created_at, user_id FROM checkins ORDER BY id"
            )
            mysql_checkins = cur.fetchall()
            for row in mysql_checkins:
                ts = row["created_at"]
                if hasattr(ts, "strftime"):
                    row["created_at"] = ts.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    row["created_at"] = str(ts)
    finally:
        mysql_conn.close()

    errors = []
    if len(sqlite_users) != mysql_users_n:
        errors.append(
            f"users 行数不一致: sqlite={len(sqlite_users)} mysql={mysql_users_n}"
        )
    if len(sqlite_checkins) != mysql_checkins_n:
        errors.append(
            f"checkins 行数不一致: sqlite真实={len(sqlite_checkins)} mysql={mysql_checkins_n}"
        )

    su = {r["id"]: dict(r) for r in sqlite_users}
    mu = {r["id"]: r for r in mysql_users}
    if set(su) != set(mu):
        errors.append("users id 集合不一致")

    sc = {r["id"]: dict(r) for r in sqlite_checkins}
    mc = {r["id"]: r for r in mysql_checkins}
    if set(sc) != set(mc):
        errors.append("checkins id 集合不一致")

    # 外键健全
    for cid, row in mc.items():
        uid = row["user_id"]
        if uid is not None and uid not in mu:
            errors.append(f"checkins id={cid} 的 user_id={uid} 在 users 中不存在")

    # 抽样比对
    user_ids = list(su.keys())
    check_ids = list(sc.keys())
    random.seed(42)
    for uid in random.sample(user_ids, min(SAMPLE, len(user_ids))):
        a, b = su[uid], mu[uid]
        for key in ("username", "password_hash", "role"):
            if a[key] != b[key]:
                errors.append(f"users id={uid} 字段 {key} 不一致")
    for cid in random.sample(check_ids, min(SAMPLE, len(check_ids))):
        a, b = sc[cid], mc[cid]
        if a["name"] != b["name"] or a["location"] != b["location"] or a["user_id"] != b["user_id"]:
            errors.append(f"checkins id={cid} 业务字段不一致")
        if a["created_at"] != b["created_at"]:
            errors.append(
                f"checkins id={cid} created_at 不一致: {a['created_at']!r} vs {b['created_at']!r}"
            )

    report = {
        "sqlite_real_counts": {
            "users": len(sqlite_users),
            "checkins": len(sqlite_checkins),
        },
        "mysql_counts": {"users": mysql_users_n, "checkins": mysql_checkins_n},
        "ok": not errors,
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)
    print("校验通过：行数、id 集合、抽样字段一致，可以考虑切换应用。")


if __name__ == "__main__":
    main()
