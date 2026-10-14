# sqlite3：Python 标准库，操作 SQLite 数据库（无需单独安装）
import logging
import sqlite3

# Path：用面向对象方式拼接、解析文件路径，避免手写字符串路径出错
from pathlib import Path

from auth import hash_password
from config import get_demo_admin_password, get_demo_student_password

logger = logging.getLogger("riqian.db")

# 项目根目录：本文件在 backend/，上两级即 web2/
ROOT = Path(__file__).resolve().parent.parent

# 数据库文件路径：web2/data/checkins.db
DB_PATH = ROOT / "data" / "checkins.db"


def get_connection():
    """打开（必要时创建）数据库连接。失败时记日志并抛出，由接口层转成友好提示。"""
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error:
        logger.exception("打开数据库失败：%s", DB_PATH)
        raise
    except OSError:
        logger.exception("创建数据目录或访问数据库文件失败：%s", DB_PATH)
        raise


def _ensure_column(conn, table: str, column: str, definition: str):
    """兼容已有库：缺列时 ALTER TABLE 补上。"""
    cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _seed_users(conn):
    """写入/同步演示账号（密码来自环境变量，只存哈希）。"""
    demos = [
        ("admin", get_demo_admin_password(), "admin"),
        ("student", get_demo_student_password(), "student"),
    ]
    for username, password, role in demos:
        password_hash = hash_password(password)
        exists = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if exists:
            # 启动时按 .env 同步演示账号密码，便于轮换弱口令
            conn.execute(
                "UPDATE users SET password_hash = ?, role = ? WHERE username = ?",
                (password_hash, role, username),
            )
        else:
            conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, password_hash, role),
            )


def init_db():
    """首次启动时建表、建索引、种子用户；已存在则跳过。"""
    conn = None
    try:
        conn = get_connection()

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('student', 'admin'))
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users (username)"
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS checkins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                user_id INTEGER REFERENCES users(id)
            )
            """
        )
        _ensure_column(conn, "checkins", "user_id", "INTEGER REFERENCES users(id)")

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_checkins_created_at ON checkins (created_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_checkins_name ON checkins (name)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_checkins_user_id ON checkins (user_id)"
        )

        _seed_users(conn)
        conn.commit()
    except (sqlite3.Error, OSError):
        logger.exception("初始化数据库失败")
        if conn is not None:
            try:
                conn.rollback()
            except sqlite3.Error:
                logger.exception("初始化失败后回滚也失败")
        raise
    finally:
        if conn is not None:
            try:
                conn.close()
            except sqlite3.Error:
                logger.exception("关闭数据库连接失败")
