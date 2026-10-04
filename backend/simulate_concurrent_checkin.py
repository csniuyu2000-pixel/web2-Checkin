"""
模拟并发打卡，观察事务行为。

说明：当前业务查重按「同一用户 / 同一姓名 + 10 分钟」，
不是按「同一位置」。所以：
  A. 两个不同用户同时打同一地点 → 通常都应成功
  B. 同一用户（或同姓名）几乎同时打两次 → 应只有 1 条成功，另 1 条 409

用法（先启动 uvicorn）：
  .\\.venv\\Scripts\\python simulate_concurrent_checkin.py
"""
import json
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "http://127.0.0.1:8000"
LOCATION = "并发测试广场"
barrier = threading.Barrier(2)  # 两个线程对齐后再发请求


def request_json(method, path, body=None, token=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        BASE + path, data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"detail": raw}
        return exc.code, payload


def login(username, password):
    code, data = request_json(
        "POST", "/api/login", {"username": username, "password": password}
    )
    if code != 200:
        raise RuntimeError(f"登录失败 {username}: {code} {data}")
    return data["token"]


def register(username, password):
    code, data = request_json(
        "POST", "/api/register", {"username": username, "password": password}
    )
    if code != 200:
        raise RuntimeError(f"注册失败 {username}: {code} {data}")
    return data["token"]


def checkin_at_same_time(label, body, token=None):
    """到达屏障后立刻打卡，尽量真正并发。"""
    barrier.wait(timeout=5)
    t0 = time.perf_counter()
    code, data = request_json("POST", "/api/checkins", body, token=token)
    ms = (time.perf_counter() - t0) * 1000
    return label, code, data, ms


def run_case(title, workers):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)
    # 新屏障，避免上一轮残留状态
    global barrier
    barrier = threading.Barrier(len(workers))

    with ThreadPoolExecutor(max_workers=len(workers)) as pool:
        futures = [pool.submit(fn) for fn in workers]
        results = [f.result() for f in as_completed(futures)]

    results.sort(key=lambda x: x[0])
    ok = 0
    for label, code, data, ms in results:
        detail = data.get("detail", data)
        if code == 200:
            ok += 1
            print(f"  [{label}] {code} 成功 id={data.get('id')} "
                  f"name={data.get('name')} loc={data.get('location')} ({ms:.0f} ms)")
        else:
            print(f"  [{label}] {code} 失败 detail={detail} ({ms:.0f} ms)")
    print(f"小结：成功 {ok} / {len(results)}")
    return results


def main():
    print("目标服务:", BASE)
    print("相同位置:", LOCATION)

    # —— 场景 A：两个不同用户，同一位置（新建账号，避免被 10 分钟限制挡住）——
    stamp = time.strftime("%H%M%S")
    token_a = register(f"user_a_{stamp}", "pass1234")
    token_b = register(f"user_b_{stamp}", "pass1234")
    run_case(
        "场景 A：两个不同用户同时打同一位置（预期：两个都成功）",
        [
            lambda: checkin_at_same_time(
                "user-A",
                {"name": f"用户甲{stamp}", "location": LOCATION},
                token_a,
            ),
            lambda: checkin_at_same_time(
                "user-B",
                {"name": f"用户乙{stamp}", "location": LOCATION},
                token_b,
            ),
        ],
    )

    # —— 场景 B：同一姓名并发两次（未登录，按 name 查重）——
    # 用新名字，避免被 10 分钟内历史记录挡住第一枪
    same_name = f"并发同名{stamp}"
    run_case(
        "场景 B：同一姓名几乎同时打两次（预期：1 成功 + 1 个 409）",
        [
            lambda: checkin_at_same_time(
                "req-1",
                {"name": same_name, "location": LOCATION},
            ),
            lambda: checkin_at_same_time(
                "req-2",
                {"name": same_name, "location": LOCATION},
            ),
        ],
    )

    print("\n如何理解：")
    print("- 事务保护的是「查重 + 插入」原子性（BEGIN IMMEDIATE）。")
    print("- 查重键是 user_id 或 name，不是 location。")
    print("- 所以「两个人同一地点」可以都成功；「同一个人连打两次」应挡下一次。")


if __name__ == "__main__":
    main()
