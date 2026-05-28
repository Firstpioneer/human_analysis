"""
AI 面试引擎核心模块
协调面试全流程：问题生成 → 追问 → 时间控制 → 记录存储
支持 LLM 增强（自动降级到规则引擎）
"""

import json
import uuid
from datetime import datetime
from typing import Optional

from .question_generator import QuestionGenerator
from .follow_up_strategy import FollowUpStrategy, TimeController
from .storage import InterviewStorage
from .llm_service import get_llm_service


class InterviewEngine:
    """AI 面试引擎 - 核心协调器"""

    def __init__(self, use_llm: bool = True):
        self._question_generator = QuestionGenerator(use_llm=use_llm)
        self._follow_up_strategy = FollowUpStrategy(use_llm=use_llm)
        self._time_controller = TimeController()
        self._storage = InterviewStorage()
        self._current_interview: Optional[dict] = None
        self._use_llm = use_llm

    def start_interview(
        self,
        profile: dict,
        candidate: Optional[dict] = None,
        total_duration: int = 45,
    ) -> dict:
        """
        开始一场新的面试

        Args:
            profile: 人才画像
            candidate: 候选人档案（可选）
            total_duration: 面试总时长（分钟）

        Returns:
            创建的面试记录
        """
        # 生成面试方案
        plan = self._question_generator.generate_plan(
            profile=profile,
            candidate=candidate,
            total_duration_minutes=total_duration,
        )

        # 初始化时间控制器
        self._time_controller.start_interview(plan)

        # 创建面试记录（保存完整画像和候选人数据，以便后续重新开始）
        interview = {
            "interview_id": f"INT_{uuid.uuid4().hex[:8].upper()}",
            "candidate": {
                "name": candidate.get("name", "未知") if candidate else "未知",
                "profile_ref": profile.get("position", {}).get("title", ""),
                "candidate_ref": candidate.get("name", "") if candidate else "",
            },
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "status": "进行中",
            "plan": plan,
            "dialogues": [],
            "evaluation": None,
            "audio_records": [],
            "_profile": profile,
            "_candidate": candidate,
            "_duration": total_duration,
        }

        # 传递画像上下文给追问策略
        self._follow_up_strategy.set_profile(profile)

        self._current_interview = interview
        self._storage.save_interview(interview)
        return interview

    def get_next_question(self, elapsed_minutes: float) -> Optional[dict]:
        """
        获取当前环节的下一问题

        Args:
            elapsed_minutes: 已用时间（分钟）

        Returns:
            问题 dict 或 None（当前环节已无问题）
        """
        if not self._current_interview:
            return None

        # 获取当前应该进行的环节
        current_section = self._time_controller.get_current_section(elapsed_minutes)
        if not current_section:
            # 面试已超出计划时间
            return self._wrap_up_question()

        section_name = current_section["section_name"]

        # 找出当前环节已问过的问题
        asked_ids = set()
        for d in self._current_interview.get("dialogues", []):
            if d.get("question_ref"):
                asked_ids.add(d["question_ref"])

        # 找当前环节未问的问题
        for section in self._current_interview["plan"]["sections"]:
            if section["section_name"] == section_name:
                for q in section.get("questions", []):
                    if q["question_id"] not in asked_ids:
                        return q

        return None

    def process_answer(
        self,
        question_id: str,
        user_answer: str,
        audio_segment: Optional[dict] = None,
    ) -> dict:
        """
        处理候选人的回答

        Args:
            question_id: 问题 ID
            user_answer: 回答文本
            audio_segment: 音频记录（可选）

        Returns:
            包含追问（如有）和时间信息的响应
        """
        if not self._current_interview:
            return {"error": "没有正在进行的面试"}

        # 获取问题信息
        question = self._question_generator.get_question_by_id(
            self._current_interview["plan"], question_id
        )

        # 记录对话
        dialogue_entry = {
            "timestamp": datetime.now().isoformat(),
            "speaker": "候选人",
            "text": user_answer,
            "transcript": user_answer,
            "question_ref": question_id,
            "duration_seconds": None,
        }
        self._current_interview["dialogues"].append(dialogue_entry)

        # 生成追问（LLM 增强版，传递对话上下文）
        follow_up = None
        if question:
            follow_up = self._follow_up_strategy.generate_follow_up(
                trigger_keywords=question.get("follow_up_triggers", []),
                user_answer=user_answer,
                question_text=question.get("question_text", ""),
                dialogue_history=self._current_interview.get("dialogues", []),
            )

        # 保存音频记录
        if audio_segment:
            self._current_interview["audio_records"].append(audio_segment)

        # 持久化
        self._storage.save_interview(self._current_interview)

        return {
            "follow_up": follow_up,
            "has_follow_up": follow_up is not None,
        }

    def ask_follow_up(self, question: str) -> dict:
        """
        AI 发出追问

        Args:
            question: 追问内容

        Returns:
            记录后的对话条目
        """
        if not self._current_interview:
            return {"error": "没有正在进行的面试"}

        entry = {
            "timestamp": datetime.now().isoformat(),
            "speaker": "AI",
            "text": question,
            "transcript": question,
            "question_ref": None,
            "duration_seconds": None,
        }
        self._current_interview["dialogues"].append(entry)
        self._storage.save_interview(self._current_interview)
        return entry

    def end_interview(self) -> dict:
        """
        结束面试并生成初步评估

        Returns:
            最终的面试记录
        """
        if not self._current_interview:
            return {"error": "没有正在进行的面试"}

        self._current_interview["end_time"] = datetime.now().isoformat()
        self._current_interview["status"] = "已完成"

        # 生成初步评估
        self._current_interview["evaluation"] = self._generate_evaluation()

        self._storage.save_interview(self._current_interview)
        result = self._current_interview
        self._current_interview = None
        return result

    def get_time_status(self, elapsed_minutes: float) -> dict:
        """获取时间状态"""
        return {
            "current_section": self._time_controller.get_current_section(elapsed_minutes),
            "remaining_time": self._time_controller.get_remaining_time(elapsed_minutes),
            "should_wrap_up": self._time_controller.should_wrap_up(elapsed_minutes),
            "suggested_action": "正常继续",
        }

    def _generate_evaluation(self) -> dict:
        """生成面试评估（优先使用 LLM，失败降级到规则引擎）"""
        # 尝试 LLM 评估
        llm = get_llm_service()
        if self._use_llm and llm.is_available:
            try:
                result = llm.evaluate_interview(self._current_interview)
                if result:
                    return result
            except Exception:
                pass

        # 降级：基于规则的简易评估
        dialogues = self._current_interview.get("dialogues", [])
        candidate_responses = [d for d in dialogues if d["speaker"] == "候选人"]

        total_answers = len(candidate_responses)
        avg_answer_length = (
            sum(len(d.get("text", "")) for d in candidate_responses) / max(total_answers, 1)
        )

        return {
            "overall_score": min(100, int(avg_answer_length / 5 + 60)),
            "dimension_scores": {
                "技术能力": 0,
                "项目经验": 0,
                "沟通表达": 0,
                "文化契合": 0,
            },
            "strengths": ["待面试完成后补充"],
            "weaknesses": ["待面试完成后补充"],
            "recommendation": "待定",
            "ai_comment": "面试记录已保存，详细评估待人工审核",
        }

    def _wrap_up_question(self) -> Optional[dict]:
        """生成收尾问题"""
        return {
            "question_id": "WRAP_UP",
            "question_text": "今天的面试到此结束。您还有什么问题想问我们吗？",
            "category": "其他",
            "difficulty": "简单",
            "expected_answer_keywords": [],
            "follow_up_triggers": [],
        }

    def get_current_interview(self) -> Optional[dict]:
        """获取当前面试状态"""
        return self._current_interview


# 便捷函数
def create_engine():
    return InterviewEngine()
