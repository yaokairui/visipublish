"""全局配置：统一从环境变量 / .env 读取，未配置时给出合理默认值。"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def resolve_chat_completions_url(base: str) -> str:
    """把网关地址归一化为完整的 chat/completions 端点。

    兼容两种写法：
    - 服务根地址：https://.../v1            -> https://.../v1/chat/completions
    - 完整端点：  https://.../v1/chat/completions（原样返回）
    """
    base = (base or "").strip().rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return base + "/chat/completions"


# ---- Vision API（留空 = 使用内置 Mock 识别，离线可演示）----
VISION_API_KEY = os.getenv("VISION_API_KEY", "").strip()
VISION_API_BASE = os.getenv("VISION_API_BASE", "https://api.openai.com/v1").strip()
VISION_MODEL = os.getenv("VISION_MODEL", "gpt-4o-mini").strip()
# 归一化后的完整请求端点（OpenAI 官方 / agnes 等兼容网关均可）
VISION_CHAT_COMPLETIONS_URL = resolve_chat_completions_url(VISION_API_BASE)

# ---- 本地模拟后台 ----
MOCK_BACKEND_HOST = os.getenv("MOCK_BACKEND_HOST", "127.0.0.1").strip()
MOCK_BACKEND_PORT = int(os.getenv("MOCK_BACKEND_PORT", "8010"))
MOCK_BACKEND_URL = os.getenv(
    "MOCK_BACKEND_URL", f"http://{MOCK_BACKEND_HOST}:{MOCK_BACKEND_PORT}"
).strip()

# ---- Playwright RPA ----
RPA_HEADLESS = os.getenv("RPA_HEADLESS", "true").strip().lower() == "true"
RPA_BROWSER = os.getenv("RPA_BROWSER", "chromium").strip()

# ---- 发布渠道 ----
# 可选：mock（本地模拟后台，默认）/ api（官方 API 骨架，未实现）
CHANNEL = os.getenv("CHANNEL", "mock").strip().lower()

# ---- 批量上架 ----
BATCH_IMAGE_LIMIT = int(os.getenv("BATCH_IMAGE_LIMIT", "20"))

# ---- Web 前端服务（FastAPI，替代旧 Streamlit 界面）----
WEB_HOST = os.getenv("WEB_HOST", "127.0.0.1").strip()
WEB_PORT = int(os.getenv("WEB_PORT", "8502"))

# ---- AI 标题生成 ----
AI_TITLE_COUNT = int(os.getenv("AI_TITLE_COUNT", "3"))
TITLE_MAX_LEN = int(os.getenv("TITLE_MAX_LEN", "60"))

# ---- 运行产物目录 ----
OUTPUT_DIR = BASE_DIR / "output"
# RPA 渠道登录态持久化目录（Mock 渠道暂不使用，预留给真实 RPA 渠道）
SESSION_DIR = BASE_DIR / os.getenv("SESSION_DIR", "output/sessions")
