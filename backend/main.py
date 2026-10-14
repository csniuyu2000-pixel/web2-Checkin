# List：类型注解，标明「打卡列表」接口返回多个 CheckinOut
import logging
import re
import sqlite3
from typing import List, Optional

# FastAPI：创建 Web 应用与路由
# Depends：注入当前登录用户
# HTTPException：业务失败时返回指定状态码
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# CORSMiddleware：跨域中间件，允许浏览器从前端页面访问本 API
from fastapi.middleware.cors import CORSMiddleware

# BaseModel / Field：定义请求与响应的数据结构
# field_validator：字段级校验（非空、长度等）
from pydantic import BaseModel, Field, field_validator

from auth import create_token, decode_token, hash_password, verify_password
from config import get_cors_origins, load_env
from db import ROOT, get_connection, init_db

load_env()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("riqian.api")

app = FastAPI(title="Daily Check-in")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Bearer token：Authorization: Bearer <token>
bearer_scheme = HTTPBearer(auto_error=False)


def raise_db_error(friendly: str, exc: Exception) -> None:
    """记录完整异常到日志，向前端只抛出友好文案。"""
    logger.exception("%s", friendly)
    raise HTTPException(status_code=500, detail=friendly) from exc


class CheckinCreate(BaseModel):
    name: str = Field(..., description="Name, 2–20 characters")
    location: str = Field(..., description="Location, required")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        text = value.strip() if isinstance(value, str) else ""
        if not text:
            raise ValueError("must not be empty")
        length = len(text)
        if length < 2 or length > 20:
            raise ValueError("must be 2–20 characters")
        return text

    @field_validator("location")
    @classmethod
    def validate_location(cls, value: str) -> str:
        text = value.strip() if isinstance(value, str) else ""
        if not text:
            raise ValueError("must not be empty")
        return text


class CheckinOut(BaseModel):
    id: int
    name: str
    location: str
    created_at: str
    user_id: Optional[int] = None


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)

    @field_validator("username", "password")
    @classmethod
    def not_blank(cls, value: str) -> str:
        text = value.strip() if isinstance(value, str) else ""
        if not text:
            raise ValueError("must not be empty")
        return text


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=72)

    @field_validator("username", "password")
    @classmethod
    def not_blank(cls, value: str) -> str:
        text = value.strip() if isinstance(value, str) else ""
        if not text:
            raise ValueError("must not be empty")
        return text


class LoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: str


class CurrentUser(BaseModel):
    id: int
    username: str
    role: str


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> CurrentUser:
    """从 Authorization Bearer token 解析当前用户；缺 token / 无效则 401。"""
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Please log in first")
    try:
        payload = decode_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user_id = int(payload["sub"])
    conn = None
    try:
        try:
            conn = get_connection()
            row = conn.execute(
                "SELECT id, username, role FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        except sqlite3.Error as exc:
            raise_db_error("Failed to load user. Please try again later.", exc)
    finally:
        if conn is not None:
            try:
                conn.close()
            except sqlite3.Error:
                logger.exception("关闭数据库连接失败")

    if row is None:
        raise HTTPException(status_code=401, detail="User not found or no longer valid")
    return CurrentUser(id=row["id"], username=row["username"], role=row["role"])


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[CurrentUser]:
    """打卡写入可带可不带 token；带了则关联 user_id。"""
    if credentials is None or not credentials.credentials:
        return None
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None


@app.exception_handler(sqlite3.Error)
async def handle_sqlite_error(request: Request, exc: sqlite3.Error):
    logger.exception("未处理的数据库错误 path=%s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Database temporarily unavailable. Please try again later."},
    )


@app.on_event("startup")
def startup():
    try:
        init_db()
    except (sqlite3.Error, OSError):
        logger.error("数据库初始化失败，服务无法正常启动")
        raise


@app.post("/api/register", response_model=LoginResponse)
def register(payload: RegisterRequest):
    """注册普通学生账号；密码写入哈希，成功后直接返回 token。"""
    conn = None
    try:
        try:
            conn = get_connection()
            exists = conn.execute(
                "SELECT id FROM users WHERE username = ?",
                (payload.username,),
            ).fetchone()
            if exists:
                raise HTTPException(status_code=409, detail="Username already taken")

            cursor = conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (payload.username, hash_password(payload.password), "student"),
            )
            conn.commit()
            user_id = cursor.lastrowid
        except HTTPException:
            raise
        except sqlite3.Error as exc:
            raise_db_error("Registration failed. Please try again later.", exc)
    finally:
        if conn is not None:
            try:
                conn.close()
            except sqlite3.Error:
                logger.exception("关闭数据库连接失败")

    token = create_token(user_id, payload.username, "student")
    return LoginResponse(
        token=token,
        user_id=user_id,
        username=payload.username,
        role="student",
    )


@app.post("/api/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    """校验用户名密码，返回 token（密码库中为哈希，从不返回明文）。"""
    conn = None
    try:
        try:
            conn = get_connection()
            row = conn.execute(
                "SELECT id, username, password_hash, role FROM users WHERE username = ?",
                (payload.username,),
            ).fetchone()
        except sqlite3.Error as exc:
            raise_db_error("Login failed. Please try again later.", exc)
    finally:
        if conn is not None:
            try:
                conn.close()
            except sqlite3.Error:
                logger.exception("关闭数据库连接失败")

    if row is None or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_token(row["id"], row["username"], row["role"])
    return LoginResponse(
        token=token,
        user_id=row["id"],
        username=row["username"],
        role=row["role"],
    )


@app.post("/api/checkins", response_model=CheckinOut)
def create_checkin(
    payload: CheckinCreate,
    user: Optional[CurrentUser] = Depends(get_optional_user),
):
    """同一事务内查重后插入；登录用户写入 user_id，便于按角色查询。"""
    conn = None
    try:
        conn = get_connection()
    except (sqlite3.Error, OSError) as exc:
        raise_db_error("Database connection failed. Please try again later.", exc)

    conn.isolation_level = None
    try:
        try:
            conn.execute("BEGIN IMMEDIATE")
            if user is not None:
                recent = conn.execute(
                    """
                    SELECT id FROM checkins
                    WHERE user_id = ?
                      AND datetime(created_at) >= datetime('now', 'localtime', '-10 minutes')
                    LIMIT 1
                    """,
                    (user.id,),
                ).fetchone()
            else:
                recent = conn.execute(
                    """
                    SELECT id FROM checkins
                    WHERE name = ?
                      AND datetime(created_at) >= datetime('now', 'localtime', '-10 minutes')
                    LIMIT 1
                    """,
                    (payload.name,),
                ).fetchone()
            if recent:
                raise HTTPException(
                    status_code=409,
                    detail="A check-in already exists within 10 minutes. Please try again later.",
                )

            cursor = conn.execute(
                "INSERT INTO checkins (name, location, user_id) VALUES (?, ?, ?)",
                (payload.name, payload.location, user.id if user else None),
            )
            row = conn.execute(
                "SELECT id, name, location, created_at, user_id FROM checkins WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
            if row is None:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to save check-in. Please try again later.",
                )

            conn.commit()
        except HTTPException:
            try:
                conn.rollback()
            except sqlite3.Error:
                logger.exception("业务失败后回滚事务失败")
            raise
        except sqlite3.Error as exc:
            try:
                conn.rollback()
            except sqlite3.Error:
                logger.exception("数据库错误后回滚事务失败")
            raise_db_error("Failed to save check-in. Please try again later.", exc)
        except Exception as exc:
            try:
                conn.rollback()
            except sqlite3.Error:
                logger.exception("未知错误后回滚事务失败")
            raise_db_error("Failed to save check-in. Please try again later.", exc)
        return dict(row)
    finally:
        if conn is not None:
            try:
                conn.close()
            except sqlite3.Error:
                logger.exception("关闭数据库连接失败")


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@app.get("/api/checkins", response_model=List[CheckinOut])
def list_checkins(
    user: CurrentUser = Depends(get_current_user),
    name: Optional[str] = Query(None, description="Filter by name (partial match)"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
):
    """需登录。admin 看全部；student 只看自己的。可选按姓名、时间段筛选。"""
    name_q = name.strip() if name else ""
    start_q = start_date.strip() if start_date else ""
    end_q = end_date.strip() if end_date else ""

    for label, value in (("Start date", start_q), ("End date", end_q)):
        if value and not _DATE_RE.match(value):
            raise HTTPException(
                status_code=422, detail=f"{label} must be YYYY-MM-DD"
            )
    if start_q and end_q and start_q > end_q:
        raise HTTPException(
            status_code=422, detail="Start date cannot be after end date"
        )

    if user.role not in ("admin", "student"):
        raise HTTPException(status_code=403, detail="Not allowed to view check-in records")

    conditions = []
    params: list = []

    # 角色范围
    if user.role == "student":
        conditions.append("(user_id = ? OR (user_id IS NULL AND name = ?))")
        params.extend([user.id, user.username])

    # 姓名模糊匹配
    if name_q:
        conditions.append("name LIKE ?")
        params.append(f"%{name_q}%")

    # 时间段（按本地日期）
    if start_q:
        conditions.append("date(created_at) >= date(?)")
        params.append(start_q)
    if end_q:
        conditions.append("date(created_at) <= date(?)")
        params.append(end_q)

    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"""
        SELECT id, name, location, created_at, user_id
        FROM checkins
        {where_sql}
        ORDER BY datetime(created_at) DESC, id DESC
    """

    conn = None
    try:
        try:
            conn = get_connection()
            rows = conn.execute(sql, params).fetchall()
        except sqlite3.Error as exc:
            raise_db_error("Failed to query check-ins. Please try again later.", exc)
        except OSError as exc:
            raise_db_error("Failed to query check-ins. Please try again later.", exc)
        return [dict(row) for row in rows]
    finally:
        if conn is not None:
            try:
                conn.close()
            except sqlite3.Error:
                logger.exception("关闭数据库连接失败")


@app.get("/")
def index():
    try:
        return FileResponse(ROOT / "index.html")
    except OSError as exc:
        logger.exception("读取首页文件失败")
        raise HTTPException(
            status_code=500,
            detail="Page temporarily unavailable. Please try again later.",
        ) from exc
