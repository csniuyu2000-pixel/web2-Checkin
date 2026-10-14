"""从环境变量读取上线相关配置（可选加载项目根目录 .env）。"""
import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv

# 项目根目录 web2/
ROOT = Path(__file__).resolve().parent.parent

_DEFAULT_CORS = "http://127.0.0.1:8000,http://localhost:8000"


def load_env() -> None:
    """加载根目录 .env；已存在的环境变量不会被覆盖。"""
    load_dotenv(ROOT / ".env")


def get_token_secret() -> bytes:
    """HMAC 签名密钥，须至少 32 字符。"""
    secret = os.environ.get("TOKEN_SECRET", "").strip()
    if len(secret) < 32:
        raise RuntimeError(
            "TOKEN_SECRET 未设置或过短（至少 32 字符）。"
            "请复制 .env.example 为 .env 并填写随机密钥。"
        )
    return secret.encode("utf-8")


def get_cors_origins() -> List[str]:
    """允许的前端来源列表；禁止使用 *。"""
    raw = os.environ.get("CORS_ORIGINS", _DEFAULT_CORS).strip()
    origins = [part.strip() for part in raw.split(",") if part.strip()]
    if not origins:
        raise RuntimeError("CORS_ORIGINS 不能为空")
    if "*" in origins:
        raise RuntimeError("CORS_ORIGINS 不允许使用 *，请填写具体来源")
    return origins


def get_demo_admin_password() -> str:
    password = os.environ.get("DEMO_ADMIN_PASSWORD", "").strip()
    if len(password) < 8:
        raise RuntimeError(
            "DEMO_ADMIN_PASSWORD 未设置或过短（至少 8 字符）。请在 .env 中配置。"
        )
    return password


def get_demo_student_password() -> str:
    password = os.environ.get("DEMO_STUDENT_PASSWORD", "").strip()
    if len(password) < 8:
        raise RuntimeError(
            "DEMO_STUDENT_PASSWORD 未设置或过短（至少 8 字符）。请在 .env 中配置。"
        )
    return password
