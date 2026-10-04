# 日签 · 打卡

带登录权限的打卡应用：学生只看自己的记录，管理员看全部。

架构见 [architecture.md](./architecture.md)，表结构见 [DB_schema.md](./DB_schema.md)。

## 当前功能

- 页面：**登录 / 注册 / 打卡 / 查询**
- 密码只存哈希；登录返回 token
- 查询按角色过滤（student / admin）；支持姓名、时间段筛选
- 姓名 2–20、位置非空（前后端都校验）
- 10 分钟内重复打卡返回 409

## 如何运行

```powershell
cd backend
.\.venv\Scripts\python -m uvicorn main:app --reload
```

浏览器打开 http://127.0.0.1:8000/（不要双击本地 html）。

## 怎么体验权限（后台人员）

1. **student / student123** 登录 → 打卡 → 点「查询」→ 只看到自己的  
2. 点「退出」  
3. **admin / admin123** 登录 → 点「查询」→ 看到全部打卡  
4. 或在「注册」新建学生账号再试

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员 |
| student | student123 | 学生 |

## 项目结构

```text
web2/
├── index.html
├── README.md
├── architecture.md
├── DB_schema.md
├── data/
└── backend/
    ├── main.py
    ├── auth.py
    ├── db.py
    └── requirements.txt
```
