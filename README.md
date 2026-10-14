# 日签 · 打卡

带登录权限的打卡应用：学生只看自己的记录，管理员看全部。

架构见 [architecture.md](./architecture.md)，表结构见 [DB_schema.md](./DB_schema.md)。

## 当前功能

- 页面：**登录 / 注册 / 打卡 / 查询**
- 密码只存哈希；登录返回 token
- 查询按角色过滤（student / admin）；支持姓名、时间段筛选
- 姓名 2–20、位置非空（前后端都校验）
- 10 分钟内重复打卡返回 409

## 上线前配置（必做）

密钥与演示密码**不再写死在代码里**，请通过环境变量配置：

1. 复制 `.env.example` 为项目根目录 `.env`
2. 填写 `TOKEN_SECRET`（≥32 字符随机串）、`DEMO_ADMIN_PASSWORD`、`DEMO_STUDENT_PASSWORD`
3. 按部署域名设置 `CORS_ORIGINS`（逗号分隔，**禁止 `*`**；本地可保持示例中的 localhost）
4. `.env` 已在 `.gitignore` 中，**不要提交到 git**

| 变量 | 说明 |
|------|------|
| `TOKEN_SECRET` | Token HMAC 密钥，至少 32 字符 |
| `CORS_ORIGINS` | 允许的前端来源，如 `http://127.0.0.1:8000,http://localhost:8000` |
| `DEMO_ADMIN_PASSWORD` | 演示管理员密码（≥8）；启动时同步到 `admin` |
| `DEMO_STUDENT_PASSWORD` | 演示学生密码（≥8）；启动时同步到 `student` |

生成密钥示例：

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

上线时请在托管平台同样配置上述变量，并把 `CORS_ORIGINS` 改成公网 HTTPS 域名。

## 如何运行

先确保根目录已有 `.env`，再安装依赖并启动：

```powershell
cd backend
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn main:app --reload
```

浏览器打开 http://127.0.0.1:8000/（不要双击本地 html）。

## 运行测试

不依赖已启动的 uvicorn，也不写入 `data/checkins.db`（每个用例用临时库；测试自带独立密钥与密码）。

```powershell
cd backend
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pytest
```

覆盖：正常打卡、10 分钟内重复打卡（409）、无 token / 假 token 查询（401）、姓名过短或位置为空（422）、学生看不到管理员打卡。

## 怎么体验权限（后台人员）

演示用户名固定为 `admin` / `student`，**密码以本地 `.env` 为准**（不要使用旧的 `admin123` / `student123`）。

1. 用 **student** + `.env` 中的 `DEMO_STUDENT_PASSWORD` 登录 → 打卡 → 点「查询」→ 只看到自己的  
2. 点「退出」  
3. 用 **admin** + `DEMO_ADMIN_PASSWORD` 登录 → 点「查询」→ 看到全部打卡  
4. 或在「注册」新建学生账号再试

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | 见 `.env` 的 `DEMO_ADMIN_PASSWORD` | 管理员 |
| student | 见 `.env` 的 `DEMO_STUDENT_PASSWORD` | 学生 |

## 项目结构

```text
web2/
├── index.html
├── .env.example
├── .env                 # 本地密钥，勿提交
├── README.md
├── architecture.md
├── DB_schema.md
├── data/
└── backend/
    ├── main.py
    ├── auth.py
    ├── config.py
    ├── db.py
    └── requirements.txt
```
