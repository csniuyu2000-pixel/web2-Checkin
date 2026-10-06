"""步骤 F：将 JSONL 导入 MySQL。密码运行时输入，不写进代码。"""
import json
import sys
from datetime import datetime
from getpass import getpass
from pathlib import Path

try:
    import pymysql
except ImportError as exc:
    raise SystemExit("请先安装：pip install pymysql") from exc

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "migrate_out"

HOST = "127.0.0.1"
PORT = 3306
USER = "root"
DATABASE = "riqian"


def parse_created_at(value: str) -> datetime:
    text = (value or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"无法解析 created_at: {value!r}")


def load_jsonl(path: Path):
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main():
    users_path = OUT_DIR / "users.jsonl"
    checkins_path = OUT_DIR / "checkins.jsonl"
    if not users_path.exists() or not checkins_path.exists():
        raise SystemExit("请先运行 02_export_sqlite.py")

    password = getpass(f"MySQL 密码（用户 {USER}@{HOST}）: ")
    users = load_jsonl(users_path)
    checkins = load_jsonl(checkins_path)

    conn = pymysql.connect(
        host=HOST,
        port=PORT,
        user=USER,
        password=password,
        database=DATABASE,
        charset="utf8mb4",
        autocommit=False,
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users")
            u_n = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM checkins")
            c_n = cur.fetchone()[0]
            if u_n or c_n:
                raise SystemExit(
                    f"目标库非空（users={u_n}, checkins={c_n}）。"
                    "请先执行 03_schema_mysql.sql 重建空表，或换库。"
                )

            cur.execute("SET FOREIGN_KEY_CHECKS=0")
            for row in users:
                cur.execute(
                    """
                    INSERT INTO users (id, username, password_hash, role)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (row["id"], row["username"], row["password_hash"], row["role"]),
                )
            for row in checkins:
                cur.execute(
                    """
                    INSERT INTO checkins (id, name, location, created_at, user_id)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        row["id"],
                        row["name"],
                        row["location"],
                        parse_created_at(row["created_at"]),
                        row["user_id"],
                    ),
                )
            cur.execute("SET FOREIGN_KEY_CHECKS=1")

            if users:
                cur.execute("SELECT MAX(id) FROM users")
                max_uid = cur.fetchone()[0] or 0
                cur.execute(f"ALTER TABLE users AUTO_INCREMENT = {max_uid + 1}")
            if checkins:
                cur.execute("SELECT MAX(id) FROM checkins")
                max_cid = cur.fetchone()[0] or 0
                cur.execute(f"ALTER TABLE checkins AUTO_INCREMENT = {max_cid + 1}")

        conn.commit()
        print("导入成功")
        print(f"  users: {len(users)}")
        print(f"  checkins: {len(checkins)}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
