"""
对话存储 — 管理对话历史的保存、加载、删除
每个对话保存为独立JSON文件，包含消息列表和关联的画像草稿
"""

import json
import os
import uuid
from datetime import datetime


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "conversations")


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def save_conversation(conversation_id: str | None, messages: list[dict], profile_draft: dict | None = None, job_title: str = "") -> str:
    """保存/更新对话"""
    ensure_data_dir()

    if not conversation_id:
        conversation_id = str(uuid.uuid4())

    filepath = os.path.join(DATA_DIR, f"{conversation_id}.json")

    # 如果已存在，保留原始创建时间
    created_at = datetime.now().isoformat()
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                old = json.load(f)
                created_at = old.get("created_at", created_at)
        except (json.JSONDecodeError, KeyError):
            pass

    # 从消息中提取岗位名称
    if not job_title and profile_draft:
        job_title = profile_draft.get("job_title", "")
    if not job_title:
        # 从用户第一条消息中截取作为标题
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


def load_conversation(conversation_id: str) -> dict | None:
    filepath = os.path.join(DATA_DIR, f"{conversation_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def delete_conversation(conversation_id: str) -> bool:
    filepath = os.path.join(DATA_DIR, f"{conversation_id}.json")
    if not os.path.exists(filepath):
        return False
    os.remove(filepath)
    return True


def list_conversations() -> list[dict]:
    """列出所有对话的摘要"""
    ensure_data_dir()
    conversations = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(DATA_DIR, filename)
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
