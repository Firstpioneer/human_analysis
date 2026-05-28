"""追问策略与时间控制模块"""
from typing import Optional
from .llm_service import get_llm_service


class FollowUpStrategy:
    def __init__(self, use_llm: bool = True):
        self._use_llm = use_llm
        self._current_profile: Optional[dict] = None

    def set_profile(self, profile: dict):
        self._current_profile = profile

    def _get_llm(self):
        if not self._use_llm:
            return None
        svc = get_llm_service()
        return svc if svc.is_available else None

    def generate_follow_up(self, trigger_keywords: list, user_answer: str,
                           question_text: str = "", dialogue_history: list = None) -> Optional[str]:
        llm = self._get_llm()
        if not llm or not self._current_profile:
            return None
        try:
            result = llm.generate_follow_up(
                question=question_text or "",
                user_answer=user_answer,
                profile=self._current_profile,
                dialogue_history=dialogue_history,
            )
            if result is not None:
                return result if result else None
        except Exception:
            pass
        return None


class TimeController:
    def __init__(self):
        self._section_times: list[dict] = []

    def start_interview(self, plan: dict):
        self._section_times = []
        elapsed = 0
        for section in plan.get("sections", []):
            self._section_times.append({
                "section_name": section["section_name"],
                "duration_minutes": section["duration_minutes"],
                "start_offset": elapsed,
                "end_offset": elapsed + section["duration_minutes"],
            })
            elapsed += section["duration_minutes"]

    def get_current_section(self, elapsed_minutes: float) -> Optional[dict]:
        for st in self._section_times:
            if st["start_offset"] <= elapsed_minutes < st["end_offset"]:
                return st
        return None

    def get_remaining_time(self, elapsed_minutes: float) -> float:
        total = sum(st["duration_minutes"] for st in self._section_times)
        return max(0, total - elapsed_minutes)

    def should_wrap_up(self, elapsed_minutes: float, warning_minutes: int = 5) -> bool:
        remaining = self.get_remaining_time(elapsed_minutes)
        return remaining <= warning_minutes

    def get_section_progress(self, elapsed_minutes: float, section_name: str) -> float:
        for st in self._section_times:
            if st["section_name"] == section_name:
                section_elapsed = elapsed_minutes - st["start_offset"]
                if st["duration_minutes"] > 0:
                    return min(1.0, section_elapsed / st["duration_minutes"])
                return 1.0
        return 0.0

    def suggest_next_action(self, elapsed_minutes: float, current_question_idx: int,
                            total_questions: int) -> str:
        remaining = self.get_remaining_time(elapsed_minutes)
        section = self.get_current_section(elapsed_minutes)
        if remaining <= 2:
            return "紧急收尾"
        if section:
            progress = self.get_section_progress(elapsed_minutes, section["section_name"])
            questions_remaining = total_questions - current_question_idx
            if progress > 0.8 and questions_remaining > 3:
                return "加快速度"
            elif progress < 0.3 and questions_remaining <= 1:
                return "深入追问"
            elif progress > 0.6 and questions_remaining > 5:
                return "精简问题"
        return "正常继续"
