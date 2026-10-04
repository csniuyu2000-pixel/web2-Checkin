# 系统架构

日签打卡应用采用前后端分离：登录后拿到 token，打卡与查询走 JSON API；查询按 token 中的 `role` 鉴权。

```text
浏览器（登录 / 注册 / 打卡 / 查询）
    ↓ HTTP / JSON + Bearer token
FastAPI（main.py + auth.py）
    ↓ sqlite3
SQLite（users / checkins）
```

## 模块划分

| 模块 | 状态 | 职责 |
|------|------|------|
| 前端 | 已实现 | 登录、注册、打卡、查询；token 存 localStorage |
| 后端 | 已实现 | 注册/登录发 token、校验、按角色查打卡、异常友好返回 |
| 数据库 | 已实现 | `users`、`checkins` |

## 前端模块

入口：`index.html`。请通过 `http://127.0.0.1:8000/` 打开。

顶部切换：**登录 / 注册 / 打卡 / 查询**。

- 登录、注册成功后保存 token，请求头带 `Authorization: Bearer …`
- 打卡：姓名 2–20、位置非空；登录后提交绑定 `user_id`
- 查询：未登录提示先登录；可按姓名（模糊）、开始/结束日期筛选；`student` 只在自己的记录里筛，`admin` 可筛全部

## 后端模块

- `auth.py`：PBKDF2 密码哈希 + HMAC token（不存明文密码）
- `db.py`：建表、种子账号、异常打日志
- `main.py`：接口与鉴权

### 权限

| role | `GET /api/checkins` |
|------|---------------------|
| admin | 全部记录 |
| student | 仅本人（`user_id`；旧数据兼容 `name = username`） |

### 校验与事务

- 姓名 2–20、位置非空（服务端必验，422）
- 10 分钟内重复打卡：事务内查重，冲突 409 并回滚
- 数据库异常：打日志，前端只收到友好 `detail`

## API 接口清单

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| GET | `/` | 无 | 首页 |
| POST | `/api/register` | 无 | 注册 student，返回 token |
| POST | `/api/login` | 无 | 登录，返回 token |
| POST | `/api/checkins` | 可选 Bearer | 打卡；登录则写 user_id |
| GET | `/api/checkins` | **必填 Bearer** | 按 role 过滤；可选 `name`、`start_date`、`end_date` |

演示账号见 [DB_schema.md](./DB_schema.md) / [README.md](./README.md)。
