"""
追问策略与时间控制模块
管理面试中的追问逻辑和面试节奏控制
追问完全由 LLM 动态生成，无任何预设追问模板
"""

from typing import Optional

from .llm_service import get_llm_service


class FollowUpStrategy:
    """追问策略引擎"""

    def __init__(self, use_llm: bool = True):
        self._use_llm = use_llm
        self._current_profile: Optional[dict] = None

    def set_profile(self, profile: dict):
        """设置当前面试的画像（LLM 追问需要上下文）"""
        self._current_profile = profile

    def _get_llm(self):
        """获取 LLM 服务（可用时）"""
        if not self._use_llm:
            return None
        svc = get_llm_service()
        return svc if svc.is_available else None

    def generate_follow_up(
        self,
        trigger_keywords: list,
        user_answer: str,
        question_text: str = "",
        dialogue_history: list = None,
    ) -> Optional[str]:
        """
        根据候选人的回答，由 LLM 动态生成追问。
        无任何预设追问模板——LLM 不可用时返回 None（不追问）。

        Args:
            trigger_keywords: 触发追问的关键词列表（仅供 LLM 参考）
            user_answer: 候选人的回答文本
            question_text: 原问题文本（LLM 需要上下文）
            dialogue_history: 最近对话历史（LLM 需要上下文）

        Returns:
            LLM 生成的追问文本；不需要追问返回 None；LLM 不可用返回 None
        """
        llm = self._get_llm()
        if not llm or not self._current_profile:
            return None  # LLM 不可用，不追问

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
    """面试时间控制器"""

    def __init__(self):
        self._section_times: list[dict] = []

    def start_interview(self, plan: dict):
        """初始化面试时间计划"""
        self._section_times = []
        elapsed = 0
        for section in plan.get("sections", []):
            self._section_times.append(
                {
                    "section_name": section["section_name"],
                    "duration_minutes": section["duration_minutes"],
                    "start_offset": elapsed,
                    "end_offset": elapsed + section["duration_minutes"],
                }
            )
            elapsed += section["duration_minutes"]

    def get_current_section(self, elapsed_minutes: float) -> Optional[dict]:
        """获取当前应该进行的环节"""
        for st in self._section_times:
            if st["start_offset"] <= elapsed_minutes < st["end_offset"]:
                return st
        return None

    def get_remaining_time(self, elapsed_minutes: float) -> float:
        """获取剩余时间（分钟）"""
        total = sum(st["duration_minutes"] for st in self._section_times)
        return max(0, total - elapsed_minutes)

    def should_wrap_up(self, elapsed_minutes: float, warning_minutes: int = 5) -> bool:
        """是否应该进入收尾阶段"""
        remaining = self.get_remaining_time(elapsed_minutes)
        return remaining <= warning_minutes

    def get_section_progress(self, elapsed_minutes: float, section_name: str) -> float:
        """获取当前环节的进度 (0.0 ~ 1.0)"""
        for st in self._section_times:
            if st["section_name"] == section_name:
                section_elapsed = elapsed_minutes - st["start_offset"]
                if st["duration_minutes"] > 0:
                    return min(1.0, section_elapsed / st["duration_minutes"])
                return 1.0
        return 0.0

    def suggest_next_action(self, elapsed_minutes: float, current_question_idx: int, total_questions: int) -> str:
        """
        根据时间情况建议下一步行动

        Returns:
            建议的行动指令
        """
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


# 便捷函数
def create_strategy():
    return FollowUpStrategy()


def create_timer():
    return TimeController()
