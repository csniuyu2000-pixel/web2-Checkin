"""插入 1 万条测试打卡，并对比插入前后（以及 name 索引前后）的查询耗时。"""
import random
import time

from db import get_connection, init_db

REPEAT = 200  # 每条 SQL 重复次数，放大微小耗时差异
INSERT_COUNT = 10_000
HOT_NAME = "张三"  # 插入后会大量重复，用来测 WHERE name = ?


def timed(conn, sql, params=(), repeat=REPEAT):
    """执行 SQL 若干次，返回平均毫秒数和最后一次结果行数。"""
    # 先跑一次，避免把解析/缓存算进计时
    rows = conn.execute(sql, params).fetchall()
    start = time.perf_counter()
    for _ in range(repeat):
        conn.execute(sql, params).fetchall()
    elapsed_ms = (time.perf_counter() - start) * 1000 / repeat
    return elapsed_ms, len(rows)


def explain(conn, sql, params=()):
    rows = conn.execute(f"EXPLAIN QUERY PLAN {sql}", params).fetchall()
    return " | ".join(row["detail"] for row in rows)


def run_suite(conn, label):
    count = conn.execute("SELECT COUNT(*) AS n FROM checkins").fetchone()["n"]
    print(f"\n===== {label}（共 {count} 行）=====")

    cases = [
        ("全表扫描", "SELECT id, name, location, created_at FROM checkins", ()),
        (
            "按时间倒序（可用 created_at 索引）",
            "SELECT id, name, location, created_at FROM checkins ORDER BY created_at DESC LIMIT 20",
            (),
        ),
        (
            f"按姓名精确查（name = '{HOT_NAME}'）",
            "SELECT id, name, location, created_at FROM checkins WHERE name = ?",
            (HOT_NAME,),
        ),
        (
            "按姓名查不存在的人",
            "SELECT id, name, location, created_at FROM checkins WHERE name = ?",
            ("不存在的人",),
        ),
    ]

    for title, sql, params in cases:
        ms, n = timed(conn, sql, params)
        plan = explain(conn, sql, params)
        print(f"{title}")
        print(f"  平均 {ms:.3f} ms / 次，本次命中 {n} 行")
        print(f"  计划: {plan}")


def insert_rows(conn, n):
    names = ["张三", "李四", "王五", "赵六", "牛宇", "yuniu"]
    locations = ["上海", "北京", "太原", "广州", "深圳", "杭州"]
    rows = [
        (random.choice(names), random.choice(locations))
        for _ in range(n)
    ]
    # 再保证 HOT_NAME 至少有一批，查询结果可观察
    rows.extend([(HOT_NAME, "上海")] * 50)
    conn.execute("BEGIN")
    conn.executemany(
        "INSERT INTO checkins (name, location) VALUES (?, ?)",
        rows,
    )
    conn.commit()
    return len(rows)


def main():
    random.seed(42)
    init_db()
    conn = get_connection()
    try:
        run_suite(conn, "插入前")

        t0 = time.perf_counter()
        added = insert_rows(conn, INSERT_COUNT)
        insert_ms = (time.perf_counter() - t0) * 1000
        print(f"\n已插入 {added} 条，耗时 {insert_ms:.1f} ms")

        run_suite(conn, "插入后（尚无 name 索引）")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_checkins_name ON checkins (name)")
        conn.commit()
        run_suite(conn, "建好 name 索引之后")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
