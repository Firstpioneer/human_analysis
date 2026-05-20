import json
import os
import uuid
from datetime import datetime


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "profiles")


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def ensure_data_dir():
    """确保数据目录存在"""
    os.makedirs(DATA_DIR, exist_ok=True)


def validate_profile(profile: dict) -> tuple[bool, list[str]]:
    """验证画像JSON的基本结构完整性"""
    errors = []
    required_fields = ["job_title", "company_context", "core_roles", "signal_dimensions"]

    for field in required_fields:
        if field not in profile:
            errors.append(f"缺少必要字段: {field}")

    if not profile.get("job_title"):
        errors.append("岗位名称为空")

    if not profile.get("signal_dimensions"):
        errors.append("信号维度为空")

    # 检查信号维度结构
    for i, cat in enumerate(profile.get("signal_dimensions", [])):
        if not cat.get("category"):
            errors.append(f"信号维度第{i+1}项缺少category")
        if not cat.get("dimensions"):
            errors.append(f"信号维度大类 '{cat.get('category', '未知')}' 下没有具体维度")
        for j, dim in enumerate(cat.get("dimensions", [])):
            if not dim.get("name"):
                errors.append(f"信号维度大类 '{cat.get('category', '未知')}' 第{j+1}项缺少name")

    return len(errors) == 0, errors


def enrich_profile(profile: dict, jd_text: str = "", conversation_summary: str = "") -> dict:
    """补充画像的元数据字段"""
    if "id" not in profile or not profile["id"]:
        profile["id"] = str(uuid.uuid4())
    if "created_at" not in profile or not profile["created_at"]:
        profile["created_at"] = datetime.now().isoformat()
    if "status" not in profile:
        profile["status"] = "draft"
    if jd_text and "jd原文" not in profile:
        profile["jd原文"] = jd_text
    if conversation_summary and "conversation_summary" not in profile:
        profile["conversation_summary"] = conversation_summary
    return profile


def save_profile(profile: dict, messages: list[dict] | None = None) -> str:
    """保存画像到JSON文件（含对话记录）"""
    ensure_data_dir()
    profile_id = profile.get("id", str(uuid.uuid4()))
    profile["id"] = profile_id

    # 将对话记录存入画像数据
    if messages:
        profile["messages"] = messages

    filepath = os.path.join(DATA_DIR, f"{profile_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder)

    return profile_id


def load_profile(profile_id: str) -> dict | None:
    """加载指定画像"""
    filepath = os.path.join(DATA_DIR, f"{profile_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def list_profiles() -> list[dict]:
    """列出所有画像的摘要"""
    ensure_data_dir()
    profiles = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(DATA_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    profiles.append({
                        "id": data.get("id", filename[:-5]),
                        "job_title": data.get("job_title", "未命名"),
                        "created_at": data.get("created_at", ""),
                        "status": data.get("status", "draft")
                    })
            except (json.JSONDecodeError, KeyError):
                continue
    # 按创建时间倒序
    profiles.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return profiles
