"""追问策略与时间控制模块（增强版）

追问分四个层级：
1. 澄清（clarify）：回答模糊或太短，请求补充
2. 深挖（deepen）：回答有内容但不够深入，追问细节
3. 真实性验证（verify）：回答匹配成功信号但缺乏细节，验证是否真做过
4. 压力测试（pressure）：发现风险信号或矛盾，深入探查
"""
import logging
from typing import Optional
from .llm_service import get_llm_service

logger = logging.getLogger(__name__)


class FollowUpStrategy:
    """智能追问策略"""

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
                           question_text: str = "", dialogue_history: list = None,
                           dimension_state: dict = None,
                           reasoning_hint: str = "",
                           needs_authenticity_check: bool = False,
                           consistency_flags: list = None) -> Optional[str]:
        """生成智能追问"""
        llm = self._get_llm()
        if not llm or not self._current_profile:
            return None

        follow_up_level = self._determine_follow_up_level(
            user_answer, dimension_state, needs_authenticity_check, consistency_flags or []
        )

        # 根据追问层级构造不同的 prompt 策略
        try:
            result = llm.generate_follow_up(
                question=question_text or "",
                user_answer=user_answer,
                profile=self._current_profile,
                dialogue_history=dialogue_history,
            )
            if result is not None:
                return result if result else None
        except Exception as e:
            logger.warning("追问生成失败: %s", e)

        return self._rule_based_follow_up(user_answer, follow_up_level, reasoning_hint)

    def _determine_follow_up_level(self, answer: str, dimension_state: dict = None,
                                   needs_authenticity_check: bool = False,
                                   consistency_flags: list = None) -> str:
        """判断追问层级"""
        answer_len = len(answer.strip())

        # 有一致性矛盾 → 压力测试
        if consistency_flags:
            return "pressure"

        # 有风险信号 → 压力测试
        if dimension_state and dimension_state.get("risk_flags"):
            return "pressure"

        # 推理引擎标记需要真实性验证 → 验证
        if needs_authenticity_check:
            return "verify"

        # 回答太短 → 澄清
        if answer_len < 30:
            return "clarify"

        # 有内容但置信度不够 → 深挖
        if dimension_state and dimension_state.get("confidence", 0) < 0.6:
            return "deepen"

        return "deepen"

    def _rule_based_follow_up(self, answer: str, level: str, hint: str = "") -> Optional[str]:
        """规则兜底追问"""
        if level == "clarify":
            if len(answer.strip()) < 10:
                return "能再展开说说吗？"
            return "能举一个具体的例子吗？"

        if level == "verify":
            # 真实性验证：追问具体操作细节
            verify_questions = [
                "能说说当时具体是怎么做的吗？",
                "这个过程中遇到过什么困难？怎么解决的？",
                "如果重新做一次，你会有什么不同的选择？",
                "当时为什么选这个方案？考虑过其他方案吗？",
            ]
            import random
            return random.choice(verify_questions)

        if level == "pressure":
            if hint and "矛盾" in hint:
                return "我注意到你之前提到的内容和现在有些不一致，能澄清一下吗？"
            return "如果重新做一次，你会有什么不同的选择？"

        if hint:
            return hint[:60]

        return None

    def should_probe_risk(self, dimension_state: dict) -> bool:
        """判断是否需要风险探查"""
        if not dimension_state:
            return False
        risk_flags = dimension_state.get("risk_flags", [])
        status = dimension_state.get("status", "")
        return status == "risk" or len(risk_flags) >= 2


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
