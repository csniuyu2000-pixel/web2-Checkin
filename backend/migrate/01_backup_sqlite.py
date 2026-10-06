"""步骤 A：备份 SQLite，并记录行数。"""
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from db import DB_PATH, get_connection  # noqa: E402

BACKUP_DIR = ROOT / "backups"


def main():
    if not DB_PATH.exists():
        raise SystemExit(f"找不到数据库：{DB_PATH}")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"checkins_{stamp}.db"

    shutil.copy2(DB_PATH, dest)

    conn = get_connection()
    try:
        users_n = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        checkins_all = conn.execute("SELECT COUNT(*) AS n FROM checkins").fetchone()["n"]
        checkins_real = conn.execute(
            "SELECT COUNT(*) AS n FROM checkins WHERE user_id IS NOT NULL"
        ).fetchone()["n"]
    finally:
        conn.close()

    print("备份完成")
    print(f"  源文件: {DB_PATH}")
    print(f"  备份到: {dest}")
    print(f"  users 全部: {users_n}")
    print(f"  checkins 全部: {checkins_all}")
    print(f"  checkins 真实(user_id 非空，将迁移): {checkins_real}")
    print(f"  将跳过压测/匿名打卡: {checkins_all - checkins_real}")


if __name__ == "__main__":
    main()
