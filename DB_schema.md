# 数据库结构

存储引擎：SQLite。库文件：`data/checkins.db`（启动后端时自动创建）。

## users（用户）

| 字段 | 类型 | 约束 | 含义 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 用户主键 |
| username | TEXT | NOT NULL UNIQUE | 登录名 |
| password_hash | TEXT | NOT NULL | 密码哈希（**不存明文**） |
| role | TEXT | NOT NULL，`student` / `admin` | 角色 |

索引：`idx_users_username`。

密码：PBKDF2-SHA256，格式 `{salt}${digest}`。

演示账号（启动时若不存在则自动创建）：

| username | 密码 | role |
|----------|------|------|
| admin | admin123 | admin |
| student | student123 | student |

## checkins（打卡记录）

| 字段 | 类型 | 约束 | 含义 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 记录主键 |
| name | TEXT | NOT NULL | 姓名（2–20，服务端校验） |
| location | TEXT | NOT NULL | 地理位置（非空） |
| created_at | TEXT | NOT NULL，默认本地时间 | 打卡时间 |
| user_id | INTEGER | 可空，REFERENCES users(id) | 登录用户打卡时写入 |

## 索引

| 名称 | 定义 | 用途 |
|------|------|------|
| idx_checkins_created_at | `created_at DESC` | 按时间列表 |
| idx_checkins_name | `name` | 按姓名查 |
| idx_checkins_user_id | `user_id` | 学生查本人记录 |

`name` 索引为 SQLite **B-Tree**：按姓名有序，避免全表扫描。

## 权限与查询

`GET /api/checkins` 必须带 token：

- **admin**：全部
- **student**：`user_id = 当前用户`，或旧数据 `user_id IS NULL AND name = username`

## 约束与校验

- 姓名长度 2–20、位置非空（服务端）
- 10 分钟内：登录用户按 `user_id` 查重，未登录按 `name` 查重；冲突 409 并回滚
