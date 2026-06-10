"""统一配置"""
import os


def _load_env_file() -> None:
    """Load simple KEY=VALUE pairs from .env without adding a hard dependency."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file()

# 服务端口
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")

# 数据目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONVERSATIONS_DIR = os.path.join(DATA_DIR, "conversations")
PROFILES_DIR = os.path.join(DATA_DIR, "profiles")
CANDIDATES_DIR = os.path.join(DATA_DIR, "candidates")
INTERVIEWS_DIR = os.path.join(DATA_DIR, "interviews")
RESUMES_DIR = os.path.join(DATA_DIR, "resumes")
CAREER_PROFILES_DIR = os.path.join(DATA_DIR, "career_profiles")

# LLM 默认配置（面试引擎用）
LLM_CONFIG_FILE = os.path.join(BASE_DIR, ".env.json")

# 简历解析 LLM 配置（OpenAI 兼容接口）
RESUME_LLM_API_KEY = (
    os.getenv("RESUME_LLM_API_KEY")
    or os.getenv("DASHSCOPE_API_KEY")
    or os.getenv("OPENAI_API_KEY")
    or ""
)
RESUME_LLM_BASE_URL = os.getenv(
    "RESUME_LLM_BASE_URL",
    os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
)
RESUME_LLM_MODEL = os.getenv("RESUME_LLM_MODEL", "qwen-max")

# 画像模块默认走 DeepSeek，也可改为 OpenAI 兼容网关。
PORTRAIT_LLM_BASE_URL = os.getenv("PORTRAIT_LLM_BASE_URL", "https://api.deepseek.com")
PORTRAIT_LLM_MODEL = os.getenv("PORTRAIT_LLM_MODEL", "deepseek-chat")

# GitHub API 可选 Token，用于提高限流额度。
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# 确保数据目录存在
for d in [CONVERSATIONS_DIR, PROFILES_DIR, CANDIDATES_DIR, INTERVIEWS_DIR, RESUMES_DIR, CAREER_PROFILES_DIR]:
    os.makedirs(d, exist_ok=True)
