# SQLite → MySQL 迁移方案

目标：把真实用户数据无损迁到本机 MySQL，校验通过后再考虑切换应用。  
原则：**先备份、再复制、校验通过才切换；失败则继续用 SQLite。**

## 已确认决策

| 项 | 决定 |
|----|------|
| MySQL | 本机已安装，用户 `root`，**运行脚本时输入密码** |
| `created_at` | MySQL 使用 **`DATETIME`**（导出字符串解析后写入） |
| 停服 | **可以**暂停后端再迁移 |
| 数据范围 | **只迁真实用户数据**：`users` 全表；`checkins` 仅 `user_id IS NOT NULL`（排除约 1 万条压测/匿名打卡） |
| 库名 | `riqian`（可在脚本常量中修改） |

写方案时统计（以导出当日 `manifest.json` 为准）：

| 表 | 全部 | 将迁移 |
|----|------|--------|
| users | 8 | 8 |
| checkins | ~10089 | 仅 `user_id` 非空（约十余条） |

---

## 总体流程

```text
① 停止 uvicorn（暂停写入）
② 01_backup_sqlite.py     → backups/checkins_*.db
③ 02_export_sqlite.py     → migrate_out/*.jsonl + manifest.json
④ mysql -u root -p < 03_schema_mysql.sql
⑤ 04_import_mysql.py      → 提示输入密码后导入
⑥ 05_verify.py            → 行数 / id 集合 / 抽样校验
⑦ 全部通过后再改后端连 MySQL（单独一步，本阶段脚本不自动改）
```

任一步失败：**不删 SQLite、不覆盖备份、应用继续连旧库。**

---

## 脚本位置

```text
backend/migrate/
  01_backup_sqlite.py
  02_export_sqlite.py
  03_schema_mysql.sql
  04_import_mysql.py
  05_verify.py
```

依赖：`pymysql`（仅迁移/校验需要）

```powershell
cd backend
.\.venv\Scripts\python -m pip install pymysql
```

---

## 操作命令（PowerShell）

**先停后端**（跑 uvicorn 的终端里 `Ctrl+C`）。

```powershell
cd "c:\Users\Think\Desktop\2026 fall 课程\AI 留学生\PPT\Ch 4 web design\web2\backend"

# 1) 备份
.\.venv\Scripts\python migrate\01_backup_sqlite.py

# 2) 导出真实数据
.\.venv\Scripts\python migrate\02_export_sqlite.py

# 3) 建库建表（会提示输入 root 密码；会 DROP 重建 riqian 下两张表）
mysql -u root -p < migrate\03_schema_mysql.sql

# 4) 导入（再次提示输入密码）
.\.venv\Scripts\python migrate\04_import_mysql.py

# 5) 校验（再次提示输入密码）
.\.venv\Scripts\python migrate\05_verify.py
```

若系统找不到 `mysql` 命令，可用 MySQL 安装目录下的客户端，或用 MySQL Workbench 打开并执行 `03_schema_mysql.sql`。

---

## 类型与导入要点

- `created_at`：SQLite 文本 → 解析为 Python `datetime` → MySQL `DATETIME`
- **保留原 `id`**，导入后设置 `AUTO_INCREMENT = MAX(id)+1`
- 先 `users` 后 `checkins`；导入中可短暂关闭外键检查
- 密码哈希**原样拷贝**，不重新 hash
- 目标表必须为空，否则导入脚本拒绝执行（防混数据）

---

## 校验门槛（不能丢数据）

`05_verify.py` 通过才算成功：

1. 行数：SQLite 真实子集 == MySQL  
2. `users` / `checkins` 的 id 集合一致  
3. 随机抽样字段一致（含 `created_at` 格式化比对）  
4. 所有非空 `user_id` 都能在 `users` 中找到  

失败则排查后：重新执行 `03` 清空重建 → `04` → `05`。

---

## 回滚

1. 不要删 `data/checkins.db` 与 `backups/`  
2. 后端继续指向 SQLite 即可恢复服务  
3. 若 SQLite 被误改，用 `backups/checkins_*.db` 拷回 `data/checkins.db`

---

## 迁移记录

| 项 | 内容 |
|----|------|
| 备份文件 | （运行 01 后填写） |
| 导出 users / checkins | （见 migrate_out/manifest.json） |
| MySQL | 127.0.0.1 / root / 库 riqian |
| 校验 | 待执行 |
| 应用是否已切 MySQL | 否（需另开任务） |

---

## 当前进度

- [x] 方案与决策  
- [x] 迁移脚本  
- [ ] 停服 + 备份 + 导出（请按上面命令执行，或让助手代跑 01/02）  
- [ ] 建表 + 导入 + 校验  
- [ ] 后端改连 MySQL（校验通过后再做）  
