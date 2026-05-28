"""简历解析结果存储"""
import json
import os
import uuid
from datetime import datetime
from typing import Optional

import config


def save_resume_result(result: dict) -> str:
    """保存简历解析结果"""
    os.makedirs(config.RESUMES_DIR, exist_ok=True)
    resume_id = result.get("resume_id", str(uuid.uuid4()))
    result["resume_id"] = resume_id
    result["saved_at"] = datetime.now().isoformat()
    filepath = os.path.join(config.RESUMES_DIR, f"{resume_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return resume_id


def load_resume_result(resume_id: str) -> Optional[dict]:
    filepath = os.path.join(config.RESUMES_DIR, f"{resume_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def delete_resume_result(resume_id: str) -> bool:
    """删除简历解析结果，返回是否成功"""
    filepath = os.path.join(config.RESUMES_DIR, f"{resume_id}.json")
    if not os.path.exists(filepath):
        return False
    os.remove(filepath)
    return True


def list_resume_results() -> list[dict]:
    os.makedirs(config.RESUMES_DIR, exist_ok=True)
    results = []
    for filename in os.listdir(config.RESUMES_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(config.RESUMES_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    results.append({
                        "resume_id": data.get("resume_id", filename[:-5]),
                        "status": data.get("status", "unknown"),
                        "saved_at": data.get("saved_at", ""),
                    })
            except (json.JSONDecodeError, KeyError):
                continue
    results.sort(key=lambda x: x.get("saved_at", ""), reverse=True)
    return results
