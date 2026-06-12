"""AI 面试引擎核心模块（集成实时推理）"""
import uuid
from datetime import datetime
from typing import Optional

from .evaluation_engine import NarrativeEvaluationEngine
from .question_generator import QuestionGenerator
from .follow_up_strategy import FollowUpStrategy, TimeController
from .quality_validator import JudgmentQualityValidator
from .reasoning_engine import InterviewReasoner


class InterviewEngine:
    def __init__(self, use_llm: bool = True):
        self._question_generator = QuestionGenerator(use_llm=use_llm)
        self._follow_up_strategy = FollowUpStrategy(use_llm=use_llm)
        self._time_controller = TimeController()
        self._reasoner = InterviewReasoner(use_llm=use_llm)
        self._current_interview: Optional[dict] = None
        self._use_llm = use_llm
        self._storage = None
        self._evaluation_engine = NarrativeEvaluationEngine()
        self._quality_validator = JudgmentQualityValidator()

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
        self._reasoner.initialize(plan, profile)

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
            "reasoning_log": [],
            "dimension_states": {},
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

        plan = self._current_interview["plan"]
        total_minutes = self._current_interview.get("_duration", 45)

        # 检查推理引擎是否建议收尾
        if not self._reasoner.should_continue(elapsed_minutes, total_minutes):
            if "WRAP_UP" not in self._get_seen_question_ids():
                question = self._wrap_up_question()
                self._record_ai_question(question)
                return question
            return None

        # 获取推理引擎的建议
        uncovered = self._reasoner.get_uncovered_dimensions()
        risk_dims = self._reasoner.get_risk_dimensions()
        reasoning_log = self._reasoner.get_reasoning_log()
        last_reasoning = reasoning_log[-1] if reasoning_log else {}

        # 确定目标维度
        target_dim_id = last_reasoning.get("target_dimension", "")
        next_hint = last_reasoning.get("next_question_hint", "")

        # 从验证维度中找匹配的问题
        if target_dim_id:
            question = self._find_question_for_dimension(plan, target_dim_id)
            if question:
                self._record_ai_question(question)
                return question

        # 如果推理引擎没有明确建议，按原逻辑遍历
        answered_ids = self._get_answered_question_ids()
        current_section = self._time_controller.get_current_section(elapsed_minutes)

        if not current_section:
            if "WRAP_UP" not in self._get_seen_question_ids():
                question = self._wrap_up_question()
                self._record_ai_question(question)
                return question
            return None

        sections = plan.get("sections", [])
        current_idx = next(
            (idx for idx, section in enumerate(sections)
             if section["section_name"] == current_section["section_name"]),
            0,
        )

        # 优先跳过已充分验证维度的问题
        verified_dim_ids = {
            d.dimension_id for d in self._reasoner._dimensions.values()
            if d.status == "verified" and d.priority != "must_have"
        }

        for offset in range(len(sections)):
            section = sections[(current_idx + offset) % len(sections)]
            for q in section.get("questions", []):
                qid = q["question_id"]
                if qid in answered_ids:
                    continue
                # 跳过已验证维度的非 must_have 问题
                linked = q.get("linked_dimension", "")
                if linked in verified_dim_ids:
                    continue
                self._record_ai_question(q)
                return q

        # 所有问题都已回答或跳过
        if "WRAP_UP" not in self._get_seen_question_ids():
            question = self._wrap_up_question()
            self._record_ai_question(question)
            return question
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
            "question_snapshot": question.get("question_text", "") if question else "",
            "duration_seconds": None,
            "is_follow_up_answer": is_follow_up_answer,
            "elapsed_seconds": elapsed_seconds,
            "client_latency_ms": client_latency_ms,
        }
        self._current_interview["dialogues"].append(dialogue_entry)

        # 触发推理引擎分析
        elapsed_minutes = (elapsed_seconds or 0) / 60
        total_minutes = self._current_interview.get("_duration", 45)
        reasoning_result = self._reasoner.analyze_answer(
            question_text=question.get("question_text", "") if question else "",
            answer_text=user_answer,
            question_category=question.get("category", "") if question else "",
            linked_dimension=question.get("linked_dimension", "") if question else "",
            elapsed_minutes=elapsed_minutes,
            total_minutes=total_minutes,
            dialogue_history=self._current_interview.get("dialogues", []),
        )

        # 保存推理日志、维度状态、声称事实
        self._current_interview["reasoning_log"] = self._reasoner.get_reasoning_log()
        self._current_interview["dimension_states"] = self._reasoner.get_dimension_states()
        self._current_interview["claimed_facts"] = self._reasoner.get_claimed_facts()

        # 决定是否追问
        follow_up = None
        follow_up_counts = self._current_interview.setdefault("follow_up_counts", {})
        current_count = follow_up_counts.get(question_id, 0)

        # 真实性验证和风险探查允许更多追问轮次
        max_follow_ups = 2
        needs_auth = reasoning_result.needs_authenticity_check if reasoning_result else False
        consistency_flags = reasoning_result.consistency_flags if reasoning_result else []
        if needs_auth or consistency_flags:
            max_follow_ups = 3

        if question and current_count < max_follow_ups:
            linked_dim = question.get("linked_dimension", "") if question else ""
            dim_state = {}
            if linked_dim:
                dim_state = self._reasoner.get_dimension_states().get(linked_dim, {})

            hint = ""
            if reasoning_result:
                if reasoning_result.action in ("deepen", "verify_authenticity", "probe_risk"):
                    hint = reasoning_result.next_question_hint

            follow_up = self._follow_up_strategy.generate_follow_up(
                trigger_keywords=question.get("follow_up_triggers", []),
                user_answer=user_answer,
                question_text=question.get("question_text", ""),
                dialogue_history=self._current_interview.get("dialogues", []),
                dimension_state=dim_state,
                reasoning_hint=hint,
                needs_authenticity_check=needs_auth,
                consistency_flags=consistency_flags,
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
            "reasoning_action": reasoning_result.action if reasoning_result else "",
            "reasoning_target": reasoning_result.target_dimension if reasoning_result else "",
        }

    def ask_follow_up(self, question: str, question_ref: Optional[str] = None) -> dict:
        if not self._current_interview:
            return {"error": "没有正在进行的面试"}
        entry = {
            "timestamp": datetime.now().isoformat(),
            "speaker": "AI",
            "text": question,
            "transcript": question,
            "question_ref": question_ref,
            "duration_seconds": None,
            "is_follow_up": True,
        }
        self._current_interview["dialogues"].append(entry)
        self._get_storage().save_interview(self._current_interview)
        return entry

    def end_interview(self) -> dict:
        if not self._current_interview:
            return {"error": "没有正在进行的面试"}
        self._current_interview["end_time"] = datetime.now().isoformat()
        self._current_interview["status"] = "已完成"
        self._current_interview["dimension_states"] = self._reasoner.get_dimension_states()
        self._current_interview["reasoning_log"] = self._reasoner.get_reasoning_log()
        self._current_interview["claimed_facts"] = self._reasoner.get_claimed_facts()
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
        return self.generate_assessment(self._current_interview)

    def generate_assessment(self, interview: dict) -> dict:
        evaluation = self._evaluation_engine.build_evaluation(interview)
        all_interviews = self._get_storage().list_interviews(limit=None)
        evaluation["quality_validation"] = self._quality_validator.validate(
            interview=interview,
            evaluation=evaluation,
            all_interviews=all_interviews,
        )
        return evaluation

    def revalidate_interview(self, interview_id: str) -> Optional[dict]:
        interview = self._get_storage().get_interview(interview_id)
        if not interview:
            return None
        interview["evaluation"] = self.generate_assessment(interview)
        self._get_storage().save_interview(interview)
        return interview

    def _find_question_for_dimension(self, plan: dict, dim_id: str) -> Optional[dict]:
        """从计划中找到关联到指定维度的下一个未回答问题"""
        answered_ids = self._get_answered_question_ids()
        for section in plan.get("sections", []):
            for q in section.get("questions", []):
                if q["question_id"] in answered_ids:
                    continue
                if q.get("linked_dimension") == dim_id:
                    return q
        return None

    def _get_answered_question_ids(self) -> set:
        ids = set()
        for d in self._current_interview.get("dialogues", []):
            if d.get("speaker") == "候选人" and d.get("question_ref"):
                ids.add(d["question_ref"])
        return ids

    def _get_seen_question_ids(self) -> set:
        ids = set()
        for d in self._current_interview.get("dialogues", []):
            if d.get("question_ref"):
                ids.add(d["question_ref"])
        return ids

    def _wrap_up_question(self) -> Optional[dict]:
        return {
            "question_id": "WRAP_UP",
            "question_text": "今天的面试就到这里，感谢你的回答。稍后系统会为你生成本次面试反馈。",
            "category": "其他",
            "difficulty": "简单",
            "expected_answer_keywords": [],
            "follow_up_triggers": [],
        }

    def get_current_interview(self) -> Optional[dict]:
        return self._current_interview

    def _record_ai_question(self, question: Optional[dict]):
        if not self._current_interview or not question:
            return
        question_id = question.get("question_id")
        dialogues = self._current_interview.setdefault("dialogues", [])
        if dialogues:
            last = dialogues[-1]
            if last.get("speaker") == "AI" and last.get("question_ref") == question_id and last.get("text") == question.get("question_text"):
                return
        dialogues.append({
            "timestamp": datetime.now().isoformat(),
            "speaker": "AI",
            "text": question.get("question_text", ""),
            "transcript": question.get("question_text", ""),
            "question_ref": question_id,
            "duration_seconds": None,
            "is_follow_up": False,
        })
        self._get_storage().save_interview(self._current_interview)
