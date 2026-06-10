"""职业画像库存储"""
import json
import os
import uuid
from datetime import datetime
from typing import Optional

import config


def _safe_id(value: str) -> str:
    return "".join(c for c in str(value) if c.isalnum() or c in ("_", "-"))


def save_career_profile(profile: dict) -> dict:
    os.makedirs(config.CAREER_PROFILES_DIR, exist_ok=True)
    now = datetime.now().isoformat()
    profile_id = _safe_id(profile.get("id") or f"CAR_{uuid.uuid4().hex[:8].upper()}")
    profile["id"] = profile_id
    profile.setdefault("created_at", now)
    profile["updated_at"] = now
    profile.setdefault("status", "active")
    filepath = os.path.join(config.CAREER_PROFILES_DIR, f"{profile_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
    return profile


def load_career_profile(profile_id: str) -> Optional[dict]:
    safe_id = _safe_id(profile_id)
    filepath = os.path.join(config.CAREER_PROFILES_DIR, f"{safe_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def list_career_profiles(limit: int = 50) -> list[dict]:
    os.makedirs(config.CAREER_PROFILES_DIR, exist_ok=True)
    profiles = []
    for filename in os.listdir(config.CAREER_PROFILES_DIR):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(config.CAREER_PROFILES_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                profiles.append(json.load(f))
        except (json.JSONDecodeError, OSError):
            continue
    profiles.sort(key=lambda item: item.get("updated_at", item.get("created_at", "")), reverse=True)
    return profiles[:limit]


def delete_career_profile(profile_id: str) -> bool:
    safe_id = _safe_id(profile_id)
    filepath = os.path.join(config.CAREER_PROFILES_DIR, f"{safe_id}.json")
    if not os.path.exists(filepath):
        return False
    os.remove(filepath)
    return True
