"""面试记录存储模块"""
import json
import os
import uuid
from datetime import datetime
from typing import Optional

import config


class InterviewStorage:
    """面试记录存储器"""

    def __init__(self, data_dir: str = None):
        self._data_dir = data_dir or config.INTERVIEWS_DIR
        self._records_dir = os.path.join(self._data_dir, "records")
        self._interviews_file = os.path.join(self._data_dir, "index.json")
        os.makedirs(self._records_dir, exist_ok=True)
        self._init_storage()

    def _init_storage(self):
        if not os.path.exists(self._interviews_file):
            self._write_json(self._interviews_file, {"interviews": []})

    def save_interview(self, interview: dict):
        interviews = self._load_all_interviews()
        found = False
        for i, existing in enumerate(interviews):
            if existing.get("interview_id") == interview.get("interview_id"):
                interviews[i] = interview
                found = True
                break
        if not found:
            interviews.append(interview)
        self._write_json(self._interviews_file, {"interviews": interviews})
        interview_file = os.path.join(self._records_dir, f"{interview['interview_id']}.json")
        self._write_json(interview_file, interview)

    def get_interview(self, interview_id: str) -> Optional[dict]:
        interviews = self._load_all_interviews()
        for i in interviews:
            if i.get("interview_id") == interview_id:
                return i
        return None

    def list_interviews(self, limit: int | None = 20) -> list:
        interviews = self._load_all_interviews()
        interviews.sort(key=lambda x: x.get("start_time", ""), reverse=True)
        if limit is None:
            return interviews
        return interviews[:limit]

    def delete_interview(self, interview_id: str) -> bool:
        interviews = self._load_all_interviews()
        new_interviews = [i for i in interviews if i.get("interview_id") != interview_id]
        if len(new_interviews) == len(interviews):
            return False
        self._write_json(self._interviews_file, {"interviews": new_interviews})
        interview_file = os.path.join(self._records_dir, f"{interview_id}.json")
        if os.path.exists(interview_file):
            os.remove(interview_file)
        return True

    def _load_all_interviews(self) -> list:
        try:
            data = self._read_json(self._interviews_file)
            return data.get("interviews", [])
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _read_json(self, filepath: str) -> dict:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_json(self, filepath: str, data: dict):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


class ProfileCandidateStorage:
    """人才画像 & 候选人档案 存储器（面试引擎专用格式）"""

    def __init__(self, data_dir: str = None):
        self._data_dir = data_dir or config.INTERVIEWS_DIR
        self._profiles_file = os.path.join(self._data_dir, "profiles.json")
        self._candidates_file = os.path.join(self._data_dir, "candidates.json")
        self._init_storage()

    def _init_storage(self):
        for f in [self._profiles_file, self._candidates_file]:
            if not os.path.exists(f):
                self._write_json(f, {"items": []})

    def save_profile(self, profile: dict) -> dict:
        items = self._load_file(self._profiles_file)
        now = datetime.now().isoformat()
        profile_id = profile.get("_id") or f"PRO_{uuid.uuid4().hex[:8].upper()}"
        profile["_id"] = profile_id
        profile.setdefault("_created_at", now)
        profile["_updated_at"] = now
        found = False
        for i, item in enumerate(items):
            if item.get("_id") == profile_id:
                items[i] = profile
                found = True
                break
        if not found:
            items.append(profile)
        self._write_json(self._profiles_file, {"items": items})
        return profile

    def get_profile(self, profile_id: str) -> Optional[dict]:
        for item in self._load_file(self._profiles_file):
            if item.get("_id") == profile_id:
                return item
        return None

    def list_profiles(self, limit: int = 20) -> list:
        items = self._load_file(self._profiles_file)
        items.sort(key=lambda x: x.get("_updated_at", ""), reverse=True)
        return items[:limit]

    def delete_profile(self, profile_id: str) -> bool:
        items = self._load_file(self._profiles_file)
        new = [i for i in items if i.get("_id") != profile_id]
        if len(new) == len(items):
            return False
        self._write_json(self._profiles_file, {"items": new})
        return True

    def save_candidate(self, candidate: dict) -> dict:
        items = self._load_file(self._candidates_file)
        now = datetime.now().isoformat()
        candidate_id = candidate.get("_id") or f"CAN_{uuid.uuid4().hex[:8].upper()}"
        candidate["_id"] = candidate_id
        candidate.setdefault("_created_at", now)
        candidate["_updated_at"] = now
        found = False
        for i, item in enumerate(items):
            if item.get("_id") == candidate_id:
                items[i] = candidate
                found = True
                break
        if not found:
            items.append(candidate)
        self._write_json(self._candidates_file, {"items": items})
        return candidate

    def get_candidate(self, candidate_id: str) -> Optional[dict]:
        for item in self._load_file(self._candidates_file):
            if item.get("_id") == candidate_id:
                return item
        return None

    def list_candidates(self, limit: int = 20) -> list:
        items = self._load_file(self._candidates_file)
        items.sort(key=lambda x: x.get("_updated_at", ""), reverse=True)
        return items[:limit]

    def delete_candidate(self, candidate_id: str) -> bool:
        items = self._load_file(self._candidates_file)
        new = [i for i in items if i.get("_id") != candidate_id]
        if len(new) == len(items):
            return False
        self._write_json(self._candidates_file, {"items": new})
        return True

    def _load_file(self, filepath: str) -> list:
        try:
            data = self._read_json(filepath)
            return data.get("items", [])
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _read_json(self, filepath: str) -> dict:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_json(self, filepath: str, data: dict):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
