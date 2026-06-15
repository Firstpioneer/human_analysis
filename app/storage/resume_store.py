"""简历解析结果存储"""
import json
import os
import uuid
from datetime import datetime
from typing import Optional

import config


def _safe_id(resume_id: str) -> str:
    """过滤 resume_id 中的非安全字符（仅保留字母数字、下划线、连字符）"""
    return "".join(c for c in resume_id if c.isalnum() or c in ("_", "-"))


def save_resume_result(result: dict) -> str:
    """保存简历解析结果"""
    os.makedirs(config.RESUMES_DIR, exist_ok=True)
    resume_id = result.get("resume_id", str(uuid.uuid4()))
    result["resume_id"] = resume_id
    result["saved_at"] = datetime.now().isoformat()
    safe_id = _safe_id(resume_id)
    result["resume_id"] = safe_id
    filepath = os.path.join(config.RESUMES_DIR, f"{safe_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return safe_id


def load_resume_result(resume_id: str) -> Optional[dict]:
    safe_id = _safe_id(resume_id)
    filepath = os.path.join(config.RESUMES_DIR, f"{safe_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def delete_resume_result(resume_id: str) -> bool:
    """删除简历解析结果，返回是否成功"""
    safe_id = _safe_id(resume_id)
    filepath = os.path.join(config.RESUMES_DIR, f"{safe_id}.json")
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
                    parsed = data.get("parsed_data", {})
                    raw_id = data.get("resume_id", filename[:-5])
                    safe_id = _safe_id(raw_id)
                    # 跳过无法通过 safe_id 定位的旧文件（文件名含中文等特殊字符）
                    if not safe_id or not os.path.exists(os.path.join(config.RESUMES_DIR, f"{safe_id}.json")):
                        continue
                    results.append({
                        "resume_id": safe_id,
                        "source_filename": data.get("source_filename", ""),
                        "status": data.get("status", "unknown"),
                        "candidate_id": data.get("candidate_id", ""),
                        "parsed_data": {
                            "name": parsed.get("name", ""),
                            "contact": parsed.get("contact", {}),
                            "claims": parsed.get("claims", [])[:5],
                            "formatted_claims": parsed.get("formatted_claims", [])[:5],
                            "objective_experiences": parsed.get("objective_experiences", [])[:5],
                            "project_experiences": parsed.get("project_experiences", [])[:5],
                            "multidimensional_profile": parsed.get("multidimensional_profile", {}),
                            "growth_potential": parsed.get("growth_potential", {}),
                            "suitable_roles": parsed.get("suitable_roles", [])[:5],
                            "interview_questions": parsed.get("interview_questions", [])[:5],
                            "digital_footprint": parsed.get("digital_footprint", {}),
                        },
                        "blind_spots": data.get("blind_spots", [])[:3],
                        "metadata": data.get("metadata", {}),
                        "saved_at": data.get("saved_at", ""),
                    })
            except (json.JSONDecodeError, KeyError):
                continue
    results.sort(key=lambda x: x.get("saved_at", ""), reverse=True)
    return results
