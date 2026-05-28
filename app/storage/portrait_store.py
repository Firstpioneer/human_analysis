"""画像存储 — 管理对话历史和画像的持久化"""
import json
import os
import uuid
from datetime import datetime
from typing import Optional

import config


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


# ==================== 对话存储 ====================

def save_conversation(conversation_id: Optional[str], messages: list[dict],
                      profile_draft: Optional[dict] = None, job_title: str = "") -> str:
    os.makedirs(config.CONVERSATIONS_DIR, exist_ok=True)
    if not conversation_id:
        conversation_id = str(uuid.uuid4())

    filepath = os.path.join(config.CONVERSATIONS_DIR, f"{conversation_id}.json")

    created_at = datetime.now().isoformat()
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                old = json.load(f)
                created_at = old.get("created_at", created_at)
        except (json.JSONDecodeError, KeyError):
            pass

    if not job_title and profile_draft:
        job_title = profile_draft.get("job_title", "")
    if not job_title:
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                job_title = content[:50].replace("\n", " ")
                if len(content) > 50:
                    job_title += "..."
                break

    data = {
        "id": conversation_id,
        "created_at": created_at,
        "updated_at": datetime.now().isoformat(),
        "job_title": job_title or "未命名对话",
        "messages": messages,
        "profile_draft": profile_draft,
        "message_count": len(messages),
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder)

    return conversation_id


def load_conversation(conversation_id: str) -> Optional[dict]:
    filepath = os.path.join(config.CONVERSATIONS_DIR, f"{conversation_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def delete_conversation(conversation_id: str) -> bool:
    filepath = os.path.join(config.CONVERSATIONS_DIR, f"{conversation_id}.json")
    if not os.path.exists(filepath):
        return False
    os.remove(filepath)
    return True


def list_conversations() -> list[dict]:
    os.makedirs(config.CONVERSATIONS_DIR, exist_ok=True)
    conversations = []
    for filename in os.listdir(config.CONVERSATIONS_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(config.CONVERSATIONS_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    conversations.append({
                        "id": data.get("id", filename[:-5]),
                        "job_title": data.get("job_title", "未命名对话"),
                        "created_at": data.get("created_at", ""),
                        "updated_at": data.get("updated_at", ""),
                        "message_count": data.get("message_count", 0),
                        "has_profile": data.get("profile_draft") is not None,
                    })
            except (json.JSONDecodeError, KeyError):
                continue
    conversations.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return conversations


# ==================== 画像存储 ====================

def validate_profile(profile: dict) -> tuple[bool, list[str]]:
    errors = []
    required_fields = ["job_title", "company_context", "core_roles", "signal_dimensions"]
    for field in required_fields:
        if field not in profile:
            errors.append(f"缺少必要字段: {field}")
    if not profile.get("job_title"):
        errors.append("岗位名称为空")
    if not profile.get("signal_dimensions"):
        errors.append("信号维度为空")
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


def save_profile(profile: dict, messages: Optional[list[dict]] = None) -> str:
    os.makedirs(config.PROFILES_DIR, exist_ok=True)
    profile_id = profile.get("id", str(uuid.uuid4()))
    profile["id"] = profile_id
    if messages:
        profile["messages"] = messages
    filepath = os.path.join(config.PROFILES_DIR, f"{profile_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder)
    return profile_id


def load_profile(profile_id: str) -> Optional[dict]:
    filepath = os.path.join(config.PROFILES_DIR, f"{profile_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def list_profiles() -> list[dict]:
    os.makedirs(config.PROFILES_DIR, exist_ok=True)
    profiles = []
    for filename in os.listdir(config.PROFILES_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(config.PROFILES_DIR, filename)
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
    profiles.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return profiles
