"""AI 面试引擎核心模块"""
import json
import uuid
from datetime import datetime
from typing import Optional

from .question_generator import QuestionGenerator
from .follow_up_strategy import FollowUpStrategy, TimeController
from .llm_service import get_llm_service


class InterviewEngine:
    def __init__(self, use_llm: bool = True):
        self._question_generator = QuestionGenerator(use_llm=use_llm)
        self._follow_up_strategy = FollowUpStrategy(use_llm=use_llm)
        self._time_controller = TimeController()
        self._current_interview: Optional[dict] = None
        self._use_llm = use_llm
        self._storage = None

    def _get_storage(self):
        if self._storage is None:
            from app.storage.interview_store import InterviewStorage
            self._storage = InterviewStorage()
        return self._storage

    def start_interview(self, profile: dict, candidate: Optional[dict] = None,
                        total_duration: int = 45) -> dict:
        plan = self._question_generator.generate_plan(
            profile=profile, candidate=candidate, total_duration_minutes=total_duration,
        )
        self._time_controller.start_interview(plan)
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
            "follow_up_counts": {},
            "_profile": profile,
            "_candidate": candidate,
            "_duration": total_duration,
        }
        self._follow_up_strategy.set_profile(profile)
        self._current_interview = interview
        self._get_storage().save_interview(interview)
        return interview

    def get_next_question(self, elapsed_minutes: float) -> Optional[dict]:
        if not self._current_interview:
            return None
        current_section = self._time_controller.get_current_section(elapsed_minutes)
        if not current_section:
            return self._wrap_up_question()
        section_name = current_section["section_name"]
        asked_ids = set()
        for d in self._current_interview.get("dialogues", []):
            if d.get("question_ref"):
                asked_ids.add(d["question_ref"])
        for section in self._current_interview["plan"]["sections"]:
            if section["section_name"] == section_name:
                for q in section.get("questions", []):
                    if q["question_id"] not in asked_ids:
                        return q
        return None

    def process_answer(self, question_id: str, user_answer: str,
                       audio_segment: Optional[dict] = None,
                       is_follow_up_answer: bool = False,
                       elapsed_seconds: Optional[int] = None,
                       client_latency_ms: Optional[int] = None) -> dict:
        if not self._current_interview:
            return {"error": "没有正在进行的面试"}
        question = self._question_generator.get_question_by_id(
            self._current_interview["plan"], question_id
        )
        dialogue_entry = {
            "timestamp": datetime.now().isoformat(),
            "speaker": "候选人",
            "text": user_answer,
            "transcript": user_answer,
            "question_ref": question_id,
            "duration_seconds": None,
            "is_follow_up_answer": is_follow_up_answer,
            "elapsed_seconds": elapsed_seconds,
            "client_latency_ms": client_latency_ms,
        }
        self._current_interview["dialogues"].append(dialogue_entry)

        follow_up = None
        follow_up_counts = self._current_interview.setdefault("follow_up_counts", {})
        current_count = follow_up_counts.get(question_id, 0)
        if question and current_count < 2:
            follow_up = self._follow_up_strategy.generate_follow_up(
                trigger_keywords=question.get("follow_up_triggers", []),
                user_answer=user_answer,
                question_text=question.get("question_text", ""),
                dialogue_history=self._current_interview.get("dialogues", []),
            )
            if follow_up:
                follow_up_counts[question_id] = current_count + 1
        if audio_segment:
            self._current_interview["audio_records"].append(audio_segment)
        self._get_storage().save_interview(self._current_interview)
        return {
            "follow_up": follow_up,
            "has_follow_up": follow_up is not None,
            "follow_up_count": follow_up_counts.get(question_id, current_count),
            "max_follow_ups": 2,
        }

    def ask_follow_up(self, question: str) -> dict:
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
        self._get_storage().save_interview(self._current_interview)
        return entry

    def end_interview(self) -> dict:
        if not self._current_interview:
            return {"error": "没有正在进行的面试"}
        self._current_interview["end_time"] = datetime.now().isoformat()
        self._current_interview["status"] = "已完成"
        self._current_interview["evaluation"] = self._generate_evaluation()
        self._get_storage().save_interview(self._current_interview)
        result = self._current_interview
        self._current_interview = None
        return result

    def get_time_status(self, elapsed_minutes: float) -> dict:
        return {
            "current_section": self._time_controller.get_current_section(elapsed_minutes),
            "remaining_time": self._time_controller.get_remaining_time(elapsed_minutes),
            "should_wrap_up": self._time_controller.should_wrap_up(elapsed_minutes),
            "suggested_action": "正常继续",
        }

    def _generate_evaluation(self) -> dict:
        llm = get_llm_service()
        if self._use_llm and llm.is_available:
            try:
                result = llm.evaluate_interview(self._current_interview)
                if result:
                    return result
            except Exception:
                pass
        dialogues = self._current_interview.get("dialogues", [])
        candidate_responses = [d for d in dialogues if d["speaker"] == "候选人"]
        total_answers = len(candidate_responses)
        avg_answer_length = (
            sum(len(d.get("text", "")) for d in candidate_responses) / max(total_answers, 1)
        )
        return {
            "overall_score": min(100, int(avg_answer_length / 5 + 60)),
            "dimension_scores": {"技术能力": 0, "项目经验": 0, "沟通表达": 0, "文化契合": 0},
            "strengths": ["待面试完成后补充"],
            "weaknesses": ["待面试完成后补充"],
            "recommendation": "待定",
            "ai_comment": "面试记录已保存，详细评估待人工审核",
        }

    def _wrap_up_question(self) -> Optional[dict]:
        return {
            "question_id": "WRAP_UP",
            "question_text": "今天的面试到此结束。您还有什么问题想问我们吗？",
            "category": "其他",
            "difficulty": "简单",
            "expected_answer_keywords": [],
            "follow_up_triggers": [],
        }

    def get_current_interview(self) -> Optional[dict]:
        return self._current_interview
