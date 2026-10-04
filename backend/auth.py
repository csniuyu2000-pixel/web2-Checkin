"""密码哈希与登录 token（标准库实现，不存明文密码）。"""
import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Dict

# 开发用签名密钥；正式环境应改为环境变量
TOKEN_SECRET = b"riqian-dev-secret-change-me"
TOKEN_TTL_SECONDS = 60 * 60 * 24  # 24 小时


def hash_password(password: str) -> str:
    """PBKDF2-SHA256：salt + 迭代哈希，库中只存 password_hash。"""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()
    return f"{salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, digest = password_hash.split("$", 1)
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()
    return hmac.compare_digest(check, digest)


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def create_token(user_id: int, username: str, role: str) -> str:
    """签发带签名的 token，载荷含 id / username / role / 过期时间。"""
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    body = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )
    sig = _b64url_encode(
        hmac.new(TOKEN_SECRET, body.encode("ascii"), hashlib.sha256).digest()
    )
    return f"{body}.{sig}"


def decode_token(token: str) -> Dict[str, Any]:
    """校验签名与过期时间，返回载荷；失败抛 ValueError。"""
    try:
        body, sig = token.split(".", 1)
    except ValueError as exc:
        raise ValueError("token 格式错误") from exc

    expect = _b64url_encode(
        hmac.new(TOKEN_SECRET, body.encode("ascii"), hashlib.sha256).digest()
    )
    if not hmac.compare_digest(sig, expect):
        raise ValueError("token 签名无效")

    payload = json.loads(_b64url_decode(body).decode("utf-8"))
    if int(payload.get("exp", 0)) < int(time.time()):
        raise ValueError("token 已过期")
    return payload
