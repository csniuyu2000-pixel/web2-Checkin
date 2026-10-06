"""步骤 E：导出真实用户数据为 JSONL（users 全表 + checkins.user_id 非空）。"""
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from db import get_connection  # noqa: E402

OUT_DIR = ROOT / "migrate_out"


def write_jsonl(path: Path, rows):
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(dict(row), ensure_ascii=False) + "\n")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    users_path = OUT_DIR / "users.jsonl"
    checkins_path = OUT_DIR / "checkins.jsonl"
    manifest_path = OUT_DIR / "manifest.json"

    conn = get_connection()
    try:
        users = conn.execute(
            "SELECT id, username, password_hash, role FROM users ORDER BY id"
        ).fetchall()
        # 真实打卡：已绑定账号的记录（排除 seed 压测与匿名打卡）
        checkins = conn.execute(
            """
            SELECT id, name, location, created_at, user_id
            FROM checkins
            WHERE user_id IS NOT NULL
            ORDER BY id
            """
        ).fetchall()
    finally:
        conn.close()

    write_jsonl(users_path, users)
    write_jsonl(checkins_path, checkins)

    manifest = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "filter": "users=ALL; checkins=WHERE user_id IS NOT NULL",
        "counts": {"users": len(users), "checkins": len(checkins)},
        "files": {
            "users.jsonl": {
                "path": str(users_path),
                "sha256": file_sha256(users_path),
                "bytes": users_path.stat().st_size,
            },
            "checkins.jsonl": {
                "path": str(checkins_path),
                "sha256": file_sha256(checkins_path),
                "bytes": checkins_path.stat().st_size,
            },
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("导出完成（仅真实用户相关打卡）")
    print(f"  users: {len(users)} -> {users_path}")
    print(f"  checkins: {len(checkins)} -> {checkins_path}")
    print(f"  manifest: {manifest_path}")


if __name__ == "__main__":
    main()
