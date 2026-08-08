"""
一键启动 / 停止项目服务（新前端栈：Flask 模拟后台 + FastAPI Web 服务）
启动：.venv\\Scripts\\python scripts\\start_project.py
停止：.venv\\Scripts\\python scripts\\start_project.py --stop
日志：output/site.log、output/backend.log、output/webapp.log
"""
import argparse
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import MOCK_BACKEND_URL, WEB_HOST, WEB_PORT  # noqa: E402

OUTPUT_DIR = BASE_DIR / "output"
PID_FILE = OUTPUT_DIR / "project.pids"
BACKEND_LOG = OUTPUT_DIR / "backend.log"
WEBAPP_LOG = OUTPUT_DIR / "webapp.log"
SITE_LOG = OUTPUT_DIR / "site.log"
SITE_PORT = 8090  # 与 scripts/serve_site.py 的 DEFAULT_PORT 保持一致
SITE_URL = f"http://127.0.0.1:{SITE_PORT}"
WEB_URL = f"http://{WEB_HOST}:{WEB_PORT}"
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def _healthy(url: str, timeout: float = 20.0) -> bool:
    import requests

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if requests.get(url, timeout=1).status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def start() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    backend = subprocess.Popen(
        [sys.executable, "-m", "mock_backend.server"],
        cwd=str(BASE_DIR),
        stdout=open(BACKEND_LOG, "ab"),
        stderr=subprocess.STDOUT,
        creationflags=CREATE_NO_WINDOW,
    )
    webapp = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "webapp.main:app",
            "--host",
            str(WEB_HOST),
            "--port",
            str(WEB_PORT),
        ],
        cwd=str(BASE_DIR),
        stdout=open(WEBAPP_LOG, "ab"),
        stderr=subprocess.STDOUT,
        creationflags=CREATE_NO_WINDOW,
    )
    site = None
    if _healthy(SITE_URL, timeout=3.0):
        print(f"导航页入口: {SITE_URL} -> 已在运行")
    else:
        site = subprocess.Popen(
            [sys.executable, str(BASE_DIR / "scripts" / "serve_site.py"), "--port", str(SITE_PORT)],
            cwd=str(BASE_DIR),
            stdout=open(SITE_LOG, "ab"),
            stderr=subprocess.STDOUT,
            creationflags=CREATE_NO_WINDOW,
        )
    pids = [backend.pid, webapp.pid] + ([site.pid] if site else [])
    PID_FILE.write_text("".join(f"{p}\n" for p in pids), encoding="utf-8")

    ok_site = _healthy(SITE_URL)
    ok_backend = _healthy(MOCK_BACKEND_URL.rstrip("/") + "/health")
    ok_webapp = _healthy(WEB_URL + "/api/config")
    print(f"导航页入口: {SITE_URL} -> {'PASS' if ok_site else 'FAIL'}")
    print(f"Web 前端(上架助手): {WEB_URL} -> {'PASS' if ok_webapp else 'FAIL'}")
    print(f"模拟后台: {MOCK_BACKEND_URL}  -> {'PASS' if ok_backend else 'FAIL'}")
    print("浏览器应已自动打开；若未打开请手动访问项目入口地址。")
    print(f"日志: {SITE_LOG} / {BACKEND_LOG} / {WEBAPP_LOG}")
    try:
        webbrowser.open(SITE_URL)
    except Exception:
        pass
    return 0 if (ok_site and ok_backend and ok_webapp) else 1


def stop() -> int:
    site_pid_file = OUTPUT_DIR / "site.pid"
    if site_pid_file.exists():
        try:
            spid = int(site_pid_file.read_text(encoding="utf-8").strip())
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(spid), "/T", "/F"], capture_output=True)
            else:
                try:
                    os.kill(spid, 15)
                except ProcessLookupError:
                    pass
            print(f"已停止导航页入口 PID {spid}")
        except Exception as exc:
            print(f"停止导航页入口失败：{exc}")
        finally:
            site_pid_file.unlink(missing_ok=True)
    if not PID_FILE.exists():
        print("未找到 PID 记录（可能未通过本脚本启动）")
        return 0
    pids = [int(x) for x in PID_FILE.read_text(encoding="utf-8").split() if x.strip()]
    for pid in pids:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
        else:
            try:
                os.kill(pid, 15)
            except ProcessLookupError:
                pass
        print(f"已停止 PID {pid}")
    PID_FILE.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stop", action="store_true", help="停止已启动的服务")
    args = parser.parse_args()
    raise SystemExit(stop() if args.stop else start())
