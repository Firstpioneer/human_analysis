"""统一配置"""
import os

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

# LLM 默认配置（面试引擎用）
LLM_CONFIG_FILE = os.path.join(BASE_DIR, ".env.json")

# 确保数据目录存在
for d in [CONVERSATIONS_DIR, PROFILES_DIR, CANDIDATES_DIR, INTERVIEWS_DIR, RESUMES_DIR]:
    os.makedirs(d, exist_ok=True)
