"""导航页（项目入口）静态服务器。

把整个仓库作为静态站点对外提供，并让 / 直接返回导航页 site/index.html。
这样导航页及其相对链接（../dashboard、../reviews）在浏览器里和本地双击一样
离线可用，也能被应用内浏览器预览（应用内浏览器不允许 file:// 地址）。

启动：.venv/Scripts/python scripts/serve_site.py [--port 8090]
"""
import argparse
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PORT = 8090
PID_FILE = BASE_DIR / "output" / "site.pid"


def _emit(msg: str) -> None:
    """安全输出：pythonw 下 stdout/stderr 为 None，不能直接 print。"""
    try:
        print(msg, flush=True)
    except Exception:
        pass


class SiteHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def _redirect_entry(self) -> bool:
        # 项目入口：/ 与 /index.html 302 重定向到导航页（保留查询串，如 ?theme=dark）。
        # 若只在服务端内部改写路径，浏览器地址栏仍是 /，assets/、../dashboard 等
        # 相对路径会解析到仓库根目录，导致图片和项目链接 404。
        parts = urlsplit(self.path)
        if parts.path in ("/", "/index.html"):
            target = "/site/index.html" + (("?" + parts.query) if parts.query else "")
            self.send_response(302)
            self.send_header("Location", target)
            self.end_headers()
            return True
        return False

    def do_GET(self):
        if not self._redirect_entry():
            return super().do_GET()

    def do_HEAD(self):
        if not self._redirect_entry():
            return super().do_HEAD()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        _emit("[site] %s" % (fmt % args))


def main() -> int:
    parser = argparse.ArgumentParser(description="YaoKr电商工具箱 · 导航页入口服务")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="监听端口")
    args = parser.parse_args()
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), SiteHandler)
    except OSError as exc:
        _emit(f"端口 {args.port} 启动失败：{exc}")
        return 1
    try:
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    except Exception as exc:
        _emit(f"PID 文件写入失败：{exc}")
    _emit(f"导航页入口: http://127.0.0.1:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())