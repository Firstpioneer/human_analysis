"""模块 D：综合评估引擎。"""
from __future__ import annotations

from datetime import datetime
import math
import re
from typing import Any

from .llm_service import get_llm_service


RISK_PHRASES = (
    "不会", "不太会", "不清楚", "不了解", "不知道", "没做过", "没有做过", "没有接触",
    "没接触", "不熟", "说不上来", "没有系统", "还没有", "暂时没有",
)


class NarrativeEvaluationEngine:
    """生成叙事化评估报告，并尽量保留旧版字段兼容前端。"""

    def build_evaluation(self, interview: dict) -> dict:
        transcript = self._build_transcript(interview)
        dimensions = self._collect_dimensions(interview.get("_profile") or {})
        base_evaluation = self._build_with_rules(interview, transcript, dimensions)
        llm = get_llm_service()

        if llm.is_available:
            try:
                llm_result = self._build_with_llm(interview, transcript, dimensions)
                if llm_result:
                    evaluation = self._normalize_llm_result(llm_result, interview, transcript, dimensions)
                    if self._is_usable_llm_evaluation(evaluation, transcript):
                        merged = self._merge_llm_overlay(base_evaluation, evaluation)
                        return self._finalize(merged, transcript)
            except Exception:
                pass

        return self._finalize(base_evaluation, transcript)

    def _build_with_llm(self, interview: dict, transcript: list[dict], dimensions: list[dict]) -> dict | None:
        llm = get_llm_service()
        profile = interview.get("_profile") or {}
        candidate = interview.get("_candidate") or {}
        transcript_text = "\n".join(
            self._format_turn_for_prompt(turn) for turn in transcript
        )
        dimension_text = "\n".join(
            f"- {dim['category']} / {dim['name']}：{dim.get('criteria') or '按候选人在该维度上的真实行为信号判断'}"
            for dim in dimensions[:18]
        )
        blind_spots = "\n".join(f"- {item}" for item in (candidate.get("_blind_spots") or [])[:10]) or "- 无"
        prompt = f"""你是一位资深招聘评估专家。请基于以下岗位画像、候选人背景和完整面试记录，生成结构化的叙事化评估报告。

必须遵守：
1. 不打分，不输出雷达图，不编造证据。
2. 每条判断尽量绑定原始证据，证据使用 turn_index 和候选人原话片段。
3. 如果信息不足，明确写“待验证”或“信息不足”，不要强行下结论。
4. 输出必须是 JSON。

岗位：{profile.get('position', {}).get('title', '未知岗位')}
岗位画像关键维度：
{dimension_text or '- 本场未提供结构化维度'}

候选人：{candidate.get('name', '未知')}
候选人简历盲区：
{blind_spots}

面试记录：
{transcript_text}

请严格返回如下 JSON 结构：
{{
  "overview": {{
    "one_line_takeaway": "一句话总结候选人最值得关注的底色"
  }},
  "unexpected_signals": [
    {{
      "title": "意料之外的信号",
      "why_it_matters": "为什么重要",
      "signal_level": "强信号|有信号|待验证|风险信号",
      "evidence": [{{"turn_index": 1, "quote": "候选人原话片段", "question": "对应问题"}}]
    }}
  ],
  "dimension_reports": [
    {{
      "dimension_name": "维度名称",
      "category": "维度分类",
      "signal_level": "强信号|有信号|待验证|风险信号",
      "judgment": "自然语言判断",
      "reasoning": "证据如何支撑判断",
      "blind_spot": "若信息不足，说明缺的是什么",
      "evidence": [{{"turn_index": 1, "quote": "候选人原话片段", "question": "对应问题"}}]
    }}
  ],
  "risks": [
    {{
      "title": "风险点",
      "severity": "高|中|低",
      "description": "风险说明",
      "blind_spot": "如有",
      "evidence": [{{"turn_index": 1, "quote": "候选人原话片段", "question": "对应问题"}}]
    }}
  ],
  "overall_judgment": {{
    "bottom_line": "这个人的底色是什么",
    "fit_assessment": "强烈推荐|推荐|待定|不推荐",
    "most_exciting_signal": "最让人兴奋的信号",
    "most_concerning_signal": "最让人犹豫的信号",
    "six_month_outlook": "如果录用，半年后最可能呈现的状态"
  }},
  "system_feedback": {{
    "signal_sufficient_dimensions": ["信号充分的维度"],
    "signal_insufficient_dimensions": [
      {{"dimension_name": "维度", "reason": "为什么不足"}}
    ],
    "question_design_suggestions": ["下次面试可怎么改问题设计"]
  }},
  "strengths": ["优势提炼"],
  "weaknesses": ["不足提炼"],
  "ai_comment": "300字以内综合评语"
}}"""
        return llm.chat_json(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="你负责生成可追溯、可质疑的面试评估报告。所有结论都必须严格锚定面试证据。",
            temperature=0.2,
            max_tokens=2200,
        )

    def _normalize_llm_result(
        self,
        result: dict,
        interview: dict,
        transcript: list[dict],
        dimensions: list[dict],
    ) -> dict:
        dimension_lookup = {(dim["category"], dim["name"]): dim for dim in dimensions}
        normalized_dimensions = []
        for item in result.get("dimension_reports") or []:
            name = (item.get("dimension_name") or "").strip()
            category = (item.get("category") or "综合判断").strip()
            base = dimension_lookup.get((category, name), {"name": name, "category": category, "criteria": ""})
            normalized_dimensions.append({
                "dimension_name": base.get("name") or name or "未命名维度",
                "category": base.get("category") or category,
                "criteria": base.get("criteria", ""),
                "signal_level": self._normalize_signal_level(item.get("signal_level")),
                "judgment": (item.get("judgment") or "").strip(),
                "reasoning": (item.get("reasoning") or "").strip(),
                "blind_spot": (item.get("blind_spot") or "").strip(),
                "evidence": self._normalize_evidence(item.get("evidence") or [], transcript),
            })

        if not normalized_dimensions:
            normalized_dimensions = self._build_with_rules(interview, transcript, dimensions)["dimension_reports"]

        overall = result.get("overall_judgment") or {}
        overview = result.get("overview") or {}
        candidate_name = interview.get("candidate", {}).get("name", "未知")
        position_title = interview.get("candidate", {}).get("profile_ref") or interview.get("_profile", {}).get("position", {}).get("title", "未知岗位")

        return {
            "version": "D-1",
            "mode": "narrative",
            "generated_at": datetime.now().isoformat(),
            "overview": {
                "candidate_name": candidate_name,
                "position_title": position_title,
                "interview_duration_minutes": self._estimate_duration_minutes(interview, transcript),
                "one_line_takeaway": (overview.get("one_line_takeaway") or "").strip(),
            },
            "unexpected_signals": [
                {
                    "title": (item.get("title") or "").strip(),
                    "why_it_matters": (item.get("why_it_matters") or "").strip(),
                    "signal_level": self._normalize_signal_level(item.get("signal_level")),
                    "evidence": self._normalize_evidence(item.get("evidence") or [], transcript),
                }
                for item in (result.get("unexpected_signals") or [])[:5]
                if item.get("title") or item.get("why_it_matters")
            ],
            "dimension_reports": normalized_dimensions,
            "risks": [
                {
                    "title": (item.get("title") or "").strip(),
                    "severity": self._normalize_severity(item.get("severity")),
                    "description": (item.get("description") or "").strip(),
                    "blind_spot": (item.get("blind_spot") or "").strip(),
                    "evidence": self._normalize_evidence(item.get("evidence") or [], transcript),
                }
                for item in (result.get("risks") or [])[:8]
                if item.get("title") or item.get("description")
            ],
            "overall_judgment": {
                "bottom_line": (overall.get("bottom_line") or "").strip(),
                "fit_assessment": self._normalize_recommendation(overall.get("fit_assessment")),
                "most_exciting_signal": (overall.get("most_exciting_signal") or "").strip(),
                "most_concerning_signal": (overall.get("most_concerning_signal") or "").strip(),
                "six_month_outlook": (overall.get("six_month_outlook") or "").strip(),
            },
            "system_feedback": self._normalize_system_feedback(result.get("system_feedback") or {}),
            "strengths": self._normalize_text_list(result.get("strengths") or []),
            "weaknesses": self._normalize_text_list(result.get("weaknesses") or []),
            "ai_comment": (result.get("ai_comment") or "").strip(),
        }

    def _build_with_rules(self, interview: dict, transcript: list[dict], dimensions: list[dict]) -> dict:
        candidate_name = interview.get("candidate", {}).get("name", "未知")
        position_title = interview.get("candidate", {}).get("profile_ref") or interview.get("_profile", {}).get("position", {}).get("title", "未知岗位")
        answers = [turn for turn in transcript if turn["speaker"] == "候选人"]
        detailed_answers = [turn for turn in answers if len(turn["text"]) >= 80]
        risk_answers = [turn for turn in answers if self._contains_risk_phrase(turn["text"])]

        dimension_reports = []
        for dimension in dimensions[:18]:
            evidence = self._select_evidence_for_dimension(dimension, transcript)
            signal_level = self._infer_signal_level(evidence)
            if signal_level == "风险信号":
                judgment = f"候选人在“{dimension['name']}”上暴露出明显不确定性，当前更像风险信号而非能力确认。"
                reasoning = "相关回答以否定、回避或缺少具体过程为主，暂时无法建立稳定正向判断。"
            elif signal_level == "强信号":
                judgment = f"候选人在“{dimension['name']}”上给出了较完整的行为证据，已形成可追溯的强信号。"
                reasoning = "回答同时包含情境、动作和结果，且能落回岗位真实问题。"
            elif signal_level == "有信号":
                judgment = f"候选人在“{dimension['name']}”上出现了可用信号，但仍需要更多交叉验证。"
                reasoning = "已经能看到一定的行为或思路依据，但证据量还不足以支撑强结论。"
            else:
                judgment = f"本场面试对“{dimension['name']}”触达不足，暂时只能保留为待验证。"
                reasoning = "当前没有足够直接的问答证据，继续判断会引入较大主观猜测。"

            dimension_reports.append({
                "dimension_name": dimension["name"],
                "category": dimension["category"],
                "criteria": dimension.get("criteria", ""),
                "signal_level": signal_level,
                "judgment": judgment,
                "reasoning": reasoning,
                "blind_spot": "" if evidence else f"缺少能直接验证“{dimension['name']}”的行为案例或追问。",
                "evidence": evidence,
            })

        sufficient_dimensions = [item["dimension_name"] for item in dimension_reports if item["signal_level"] in {"强信号", "有信号"}]
        insufficient_dimensions = [
            {"dimension_name": item["dimension_name"], "reason": item["blind_spot"] or "本场证据不足"}
            for item in dimension_reports if item["signal_level"] == "待验证"
        ]

        risks = self._build_risks(interview, transcript, dimension_reports, risk_answers)
        recommendation = self._infer_recommendation(dimension_reports, risks)
        most_exciting = next((item["judgment"] for item in dimension_reports if item["signal_level"] == "强信号"), "")
        most_concerning = next((risk["description"] for risk in risks if risk["severity"] in {"高", "中"}), "") or next(
            (item["judgment"] for item in dimension_reports if item["signal_level"] == "风险信号"),
            "",
        )
        takeaway = self._build_takeaway(dimension_reports, risks, detailed_answers, answers)

        return {
            "version": "D-1",
            "mode": "narrative",
            "generated_at": datetime.now().isoformat(),
            "overview": {
                "candidate_name": candidate_name,
                "position_title": position_title,
                "interview_duration_minutes": self._estimate_duration_minutes(interview, transcript),
                "one_line_takeaway": takeaway,
            },
            "unexpected_signals": self._build_unexpected_signals(interview, transcript),
            "dimension_reports": dimension_reports,
            "risks": risks,
            "overall_judgment": {
                "bottom_line": self._build_bottom_line(dimension_reports, risks, answers),
                "fit_assessment": recommendation,
                "most_exciting_signal": most_exciting or "尚未形成足够强的超预期信号。",
                "most_concerning_signal": most_concerning or "当前更大的问题是样本不足，而非明确负向信号。",
                "six_month_outlook": self._build_six_month_outlook(recommendation, sufficient_dimensions, insufficient_dimensions),
            },
            "system_feedback": {
                "signal_sufficient_dimensions": sufficient_dimensions[:6],
                "signal_insufficient_dimensions": insufficient_dimensions[:6],
                "question_design_suggestions": self._build_question_suggestions(insufficient_dimensions, interview),
            },
            "strengths": [item["dimension_name"] for item in dimension_reports if item["signal_level"] == "强信号"][:5],
            "weaknesses": [risk["title"] for risk in risks][:5] or [item["dimension_name"] for item in dimension_reports if item["signal_level"] == "风险信号"][:5],
            "ai_comment": self._build_ai_comment(takeaway, recommendation, most_exciting, most_concerning),
        }

    def _finalize(self, evaluation: dict, transcript: list[dict]) -> dict:
        evaluation["recommendation"] = self._normalize_recommendation(
            evaluation.get("overall_judgment", {}).get("fit_assessment") or evaluation.get("recommendation")
        )
        evaluation["overall_score"] = None
        evaluation["dimension_scores"] = {}
        evaluation.setdefault("strengths", [])
        evaluation.setdefault("weaknesses", [])
        evaluation.setdefault("ai_comment", evaluation.get("overview", {}).get("one_line_takeaway", ""))
        evaluation["traceability"] = {
            "judgment_count": len(evaluation.get("dimension_reports") or []) + len(evaluation.get("risks") or []),
            "evidence_item_count": sum(len(item.get("evidence") or []) for item in evaluation.get("dimension_reports") or [])
            + sum(len(item.get("evidence") or []) for item in evaluation.get("risks") or []),
            "candidate_turns": len([turn for turn in transcript if turn["speaker"] == "候选人"]),
            "total_turns": len(transcript),
        }
        evaluation["jd_match_report"] = self._build_jd_match_report(evaluation)
        evaluation["analysis_process"] = self._build_analysis_process(evaluation)
        evaluation["overall_report"] = self._build_overall_report(evaluation)
        return evaluation

    def _build_transcript(self, interview: dict) -> list[dict]:
        lookup = {}
        for section in (interview.get("plan") or {}).get("sections", []):
            for question in section.get("questions", []):
                lookup[question.get("question_id")] = question.get("question_text", "")

        transcript = []
        for idx, entry in enumerate(interview.get("dialogues") or [], start=1):
            question_ref = entry.get("question_ref")
            question_text = entry.get("question_snapshot") or lookup.get(question_ref, "")
            transcript.append({
                "turn_index": idx,
                "speaker": entry.get("speaker", ""),
                "text": (entry.get("text") or entry.get("transcript") or "").strip(),
                "question_ref": question_ref,
                "question_text": question_text,
                "is_follow_up": bool(entry.get("is_follow_up")),
                "timestamp": entry.get("timestamp"),
            })
        return transcript

    def _collect_dimensions(self, profile: dict) -> list[dict]:
        dimensions = []
        seen = set()
        for group in profile.get("_signal_dimensions") or []:
            category = group.get("category", "综合判断")
            for item in group.get("dimensions") or []:
                name = (item.get("name") or "").strip()
                if not name or name in seen:
                    continue
                seen.add(name)
                dimensions.append({
                    "category": category,
                    "name": name,
                    "criteria": item.get("evaluation_criteria") or item.get("description") or "",
                })

        extra_groups = [
            ("必须验证", profile.get("_must_have") or []),
            ("加分信号", profile.get("_nice_to_have") or []),
            ("风险画像", profile.get("_anti_profile") or []),
        ]
        for category, items in extra_groups:
            for raw in items:
                name = str(raw).strip()
                if not name or name in seen:
                    continue
                seen.add(name)
                dimensions.append({"category": category, "name": name, "criteria": ""})

        if not dimensions:
            for skill in (profile.get("requirements") or {}).get("skills") or []:
                name = (skill.get("name") or "").strip()
                if not name or name in seen:
                    continue
                seen.add(name)
                dimensions.append({"category": "岗位能力", "name": name, "criteria": ""})
        return dimensions

    def _select_evidence_for_dimension(self, dimension: dict, transcript: list[dict], limit: int = 2) -> list[dict]:
        keywords = self._extract_keywords(
            f"{dimension.get('category', '')} {dimension.get('name', '')} {dimension.get('criteria', '')}"
        )
        candidates = []
        for turn in transcript:
            if turn["speaker"] != "候选人" or not turn["text"]:
                continue
            haystack = f"{turn.get('question_text', '')} {turn['text']}"
            score = self._score_keywords(haystack, keywords)
            if score <= 0:
                continue
            candidates.append((score, len(turn["text"]), turn))

        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        evidence = []
        for _, _, turn in candidates[:limit]:
            evidence.append({
                "turn_index": turn["turn_index"],
                "question_id": turn.get("question_ref"),
                "question": turn.get("question_text", ""),
                "quote": self._truncate(turn["text"], 120),
                "source": "interview_transcript",
            })
        return evidence

    def _build_risks(
        self,
        interview: dict,
        transcript: list[dict],
        dimension_reports: list[dict],
        risk_answers: list[dict],
    ) -> list[dict]:
        risks = []
        anti_profile = (interview.get("_profile") or {}).get("_anti_profile") or []
        for raw in anti_profile[:4]:
            dim_name = str(raw).strip()
            related = next((item for item in dimension_reports if item["dimension_name"] == dim_name), None)
            if not related:
                continue
            severity = "高" if related["signal_level"] == "风险信号" else "中" if related["signal_level"] == "待验证" else "低"
            risks.append({
                "title": dim_name,
                "severity": severity,
                "description": f"岗位画像已将“{dim_name}”标记为关键风险画像，本场需要重点复核候选人是否存在结构性错配。",
                "blind_spot": related.get("blind_spot", ""),
                "evidence": related.get("evidence", []),
            })

        if risk_answers:
            top_risk = risk_answers[0]
            risks.append({
                "title": "关键回答存在明显不确定性",
                "severity": "中",
                "description": "候选人在部分核心问答里出现了直接否定、回避或缺少过程的回答，需要人工复核是否只是样本不足。",
                "blind_spot": "",
                "evidence": [{
                    "turn_index": top_risk["turn_index"],
                    "question_id": top_risk.get("question_ref"),
                    "question": top_risk.get("question_text", ""),
                    "quote": self._truncate(top_risk["text"], 120),
                    "source": "interview_transcript",
                }],
            })

        return risks[:8]

    def _build_unexpected_signals(self, interview: dict, transcript: list[dict]) -> list[dict]:
        candidate = interview.get("_candidate") or {}
        unexpected = []
        if candidate.get("external_profiles", {}).get("github_activity"):
            unexpected.append({
                "title": "存在额外公开技术活动信号",
                "why_it_matters": "这说明候选人的技术兴趣不完全停留在简历声明层面，可能具备更强的自驱探索倾向。",
                "signal_level": "有信号",
                "evidence": [{
                    "turn_index": 0,
                    "question_id": None,
                    "question": "候选人外部公开信息",
                    "quote": str(candidate["external_profiles"].get("github_activity")),
                    "source": "candidate_profile",
                }],
            })

        proactive = next(
            (turn for turn in transcript if turn["speaker"] == "候选人" and any(word in turn["text"] for word in ("主动", "自学", "自己做", "比赛", "尝试"))),
            None,
        )
        if proactive:
            unexpected.append({
                "title": "出现了主动探索型表达",
                "why_it_matters": "对于需要从零定义工作方式的岗位，这类主动性比单纯知识覆盖更重要。",
                "signal_level": "有信号",
                "evidence": [{
                    "turn_index": proactive["turn_index"],
                    "question_id": proactive.get("question_ref"),
                    "question": proactive.get("question_text", ""),
                    "quote": self._truncate(proactive["text"], 120),
                    "source": "interview_transcript",
                }],
            })
        return unexpected[:4]

    def _build_takeaway(
        self,
        dimension_reports: list[dict],
        risks: list[dict],
        detailed_answers: list[dict],
        answers: list[dict],
    ) -> str:
        strong_count = len([item for item in dimension_reports if item["signal_level"] == "强信号"])
        risk_count = len([item for item in dimension_reports if item["signal_level"] == "风险信号"]) + len(risks)
        detail_ratio = 0 if not answers else len(detailed_answers) / len(answers)
        if strong_count >= 3 and risk_count == 0:
            return "整体呈现出较强的成长潜力和可追溯行为证据，更像可以继续深挖的候选人。"
        if risk_count >= 3:
            return "当前最突出的问题不是能力高低，而是关键维度证据薄弱且伴随多处风险信号。"
        if detail_ratio >= 0.5:
            return "回答里已经能看到一定深度，但哪些能力是真实力、哪些只是初步直觉，仍需下一轮验证。"
        return "这位候选人的轮廓已经初步出现，但仍以待验证信号为主，不能过早下结论。"

    def _build_bottom_line(self, dimension_reports: list[dict], risks: list[dict], answers: list[dict]) -> str:
        strong_dims = [item["dimension_name"] for item in dimension_reports if item["signal_level"] == "强信号"][:3]
        risk_dims = [item["dimension_name"] for item in dimension_reports if item["signal_level"] == "风险信号"][:2]
        if strong_dims and not risk_dims:
            return f"候选人的底色更接近“能把问题讲清并给出行为证据的人”，当前最可信的维度是：{'、'.join(strong_dims)}。"
        if risk_dims:
            return f"候选人的核心风险不是单点不会，而是关键维度目前仍缺少稳定证据，尤其是：{'、'.join(risk_dims)}。"
        if answers:
            return "目前能看到一定思考，但更多结论仍停留在待验证阶段，下一轮应围绕高价值盲区继续追问。"
        return "本场缺少足够面试样本，无法形成可靠底色判断。"

    def _build_six_month_outlook(
        self,
        recommendation: str,
        sufficient_dimensions: list[str],
        insufficient_dimensions: list[dict],
    ) -> str:
        if recommendation in {"强烈推荐", "推荐"}:
            return f"如果进入团队并获得明确带教，较可能先在“{'、'.join(sufficient_dimensions[:2]) or '已验证维度'}”上快速形成贡献。"
        if recommendation == "不推荐":
            return "若直接录用，半年后更可能仍停留在适应岗位语言和补足关键盲区的阶段。"
        return f"若继续推进，半年后的上限取决于其能否把“{(insufficient_dimensions[0]['dimension_name'] if insufficient_dimensions else '关键盲区')}”补成稳定能力。"

    def _build_question_suggestions(self, insufficient_dimensions: list[dict], interview: dict) -> list[str]:
        suggestions = []
        for item in insufficient_dimensions[:4]:
            suggestions.append(f"围绕“{item['dimension_name']}”补一题要求候选人讲具体情境、动作和结果的行为题。")
        if (interview.get("_candidate") or {}).get("_blind_spots"):
            suggestions.append("针对简历盲区单独设计核验题，避免候选人一直停留在抽象表态。")
        if not suggestions:
            suggestions.append("下一轮优先使用追问式问题，验证当前已出现的正向信号是否稳定。")
        return suggestions[:5]

    def _build_ai_comment(self, takeaway: str, recommendation: str, exciting: str, concerning: str) -> str:
        parts = [takeaway]
        parts.append(f"当前建议为“{recommendation}”。")
        if exciting:
            parts.append(f"最值得继续深挖的是：{exciting}")
        if concerning:
            parts.append(f"最需要复核的是：{concerning}")
        return " ".join(parts)

    def _infer_signal_level(self, evidence: list[dict]) -> str:
        if not evidence:
            return "待验证"
        joined = " ".join(item.get("quote", "") for item in evidence)
        if self._contains_risk_phrase(joined):
            return "风险信号"
        if len(evidence) >= 2 and sum(len(item.get("quote", "")) for item in evidence) >= 100:
            return "强信号"
        return "有信号"

    def _infer_recommendation(self, dimension_reports: list[dict], risks: list[dict]) -> str:
        strong_count = len([item for item in dimension_reports if item["signal_level"] == "强信号"])
        positive_count = len([item for item in dimension_reports if item["signal_level"] in {"强信号", "有信号"}])
        risk_count = len([item for item in dimension_reports if item["signal_level"] == "风险信号"])
        unsupported_count = len([item for item in dimension_reports if item["signal_level"] == "待验证"])
        if strong_count >= 4 and risk_count == 0 and len(risks) <= 1:
            return "强烈推荐"
        if positive_count >= 3 and risk_count <= 1:
            return "推荐"
        if risk_count >= 3 or unsupported_count >= max(5, math.ceil(len(dimension_reports) * 0.6)):
            return "不推荐"
        return "待定"

    def _estimate_duration_minutes(self, interview: dict, transcript: list[dict]) -> int:
        start = interview.get("start_time")
        end = interview.get("end_time")
        if start and end:
            try:
                delta = datetime.fromisoformat(end) - datetime.fromisoformat(start)
                return max(1, int(delta.total_seconds() // 60))
            except ValueError:
                pass
        return max(1, len(transcript) // 3) if transcript else 0

    def _normalize_signal_level(self, value: Any) -> str:
        text = str(value or "").strip()
        if text in {"强信号", "有信号", "待验证", "风险信号"}:
            return text
        if "风险" in text:
            return "风险信号"
        if "强" in text:
            return "强信号"
        if "待" in text or "不足" in text:
            return "待验证"
        return "有信号" if text else "待验证"

    def _normalize_recommendation(self, value: Any) -> str:
        text = str(value or "").strip()
        if text in {"强烈推荐", "推荐", "待定", "不推荐"}:
            return text
        if "不" in text:
            return "不推荐"
        if "强" in text:
            return "强烈推荐"
        if "推" in text:
            return "推荐"
        return "待定"

    def _normalize_severity(self, value: Any) -> str:
        text = str(value or "").strip()
        if text in {"高", "中", "低"}:
            return text
        if "高" in text:
            return "高"
        if "低" in text:
            return "低"
        return "中"

    def _normalize_system_feedback(self, payload: dict) -> dict:
        sufficient = self._normalize_text_list(payload.get("signal_sufficient_dimensions") or [])
        insufficient = []
        for item in payload.get("signal_insufficient_dimensions") or []:
            if isinstance(item, dict):
                name = (item.get("dimension_name") or "").strip()
                reason = (item.get("reason") or "").strip()
                if name or reason:
                    insufficient.append({"dimension_name": name or "未命名维度", "reason": reason or "本场信息不足"})
            elif item:
                insufficient.append({"dimension_name": str(item).strip(), "reason": "本场信息不足"})
        return {
            "signal_sufficient_dimensions": sufficient[:8],
            "signal_insufficient_dimensions": insufficient[:8],
            "question_design_suggestions": self._normalize_text_list(payload.get("question_design_suggestions") or [])[:6],
        }

    def _normalize_evidence(self, evidence_items: list[dict], transcript: list[dict]) -> list[dict]:
        turn_lookup = {turn["turn_index"]: turn for turn in transcript}
        normalized = []
        for item in evidence_items[:5]:
            if not isinstance(item, dict):
                continue
            turn_index = item.get("turn_index")
            turn = turn_lookup.get(turn_index)
            normalized.append({
                "turn_index": turn_index if isinstance(turn_index, int) else 0,
                "question_id": item.get("question_id") or (turn.get("question_ref") if turn else None),
                "question": (item.get("question") or (turn.get("question_text") if turn else "") or "").strip(),
                "quote": self._truncate((item.get("quote") or (turn.get("text") if turn else "") or "").strip(), 120),
                "source": item.get("source") or ("interview_transcript" if turn else "generated"),
            })
        return [item for item in normalized if item["quote"] or item["question"]]

    def _normalize_text_list(self, items: list[Any]) -> list[str]:
        return [str(item).strip() for item in items if str(item).strip()]

    def _build_analysis_process(self, evaluation: dict) -> list[dict]:
        dimension_reports = evaluation.get("dimension_reports") or []
        strong_items = [item for item in dimension_reports if item.get("signal_level") == "强信号"]
        partial_items = [item for item in dimension_reports if item.get("signal_level") == "有信号"]
        pending_items = [item for item in dimension_reports if item.get("signal_level") == "待验证"]
        risk_items = evaluation.get("risks") or []

        return [
            {
                "step": 1,
                "name": "抽取岗位判断维度",
                "purpose": "先把 JD/画像 拆成可验证的能力与风险维度，避免直接凭感觉评价候选人。",
                "inputs": self._collect_analysis_inputs(dimension_reports, max_items=8),
                "method": "读取岗位画像中的 signal_dimensions、must_have、anti_profile，并映射为面试判断维度。",
                "output": f"共识别出 {len(dimension_reports)} 个需要判断的岗位维度。",
            },
            {
                "step": 2,
                "name": "绑定候选人原始证据",
                "purpose": "每个能力结论都必须回到候选人的具体回答，而不是自我陈述标签。",
                "inputs": [item.get("dimension_name") for item in strong_items[:4]] or [item.get("dimension_name") for item in partial_items[:4]],
                "method": "对每个维度检索最相关的候选人回答，优先保留包含情境、动作、结果的片段作为证据。",
                "output": f"形成 {evaluation.get('traceability', {}).get('evidence_item_count', 0)} 条可追溯证据。",
            },
            {
                "step": 3,
                "name": "形成能力判断",
                "purpose": "把零散回答收束成岗位相关的能力结论，并区分强信号、部分信号和待验证项。",
                "inputs": [item.get("dimension_name") for item in strong_items[:4] + partial_items[:4]],
                "method": "结合证据密度、回答具体度、是否落到真实业务场景，形成维度级判断。",
                "output": f"强信号 {len(strong_items)} 项，部分信号 {len(partial_items)} 项，待验证 {len(pending_items)} 项。",
            },
            {
                "step": 4,
                "name": "结合 JD 做适配与差距分析",
                "purpose": "不是只看候选人是否不错，而是看他和这个岗位要求之间的匹配与缺口。",
                "inputs": self._collect_analysis_inputs((evaluation.get("jd_match_report") or {}).get("gap_requirements") or [], key="requirement", max_items=6),
                "method": "将候选人已验证能力与 JD 核心要求逐项对照，区分已匹配、部分匹配和明显缺口。",
                "output": f"识别出 {len((evaluation.get('jd_match_report') or {}).get('matched_requirements') or [])} 项匹配要求，"
                          f"{len((evaluation.get('jd_match_report') or {}).get('gap_requirements') or [])} 项差距/不足。",
            },
            {
                "step": 5,
                "name": "汇总整体结论",
                "purpose": "在能力、证据、岗位要求和风险之间做最后综合判断。",
                "inputs": [evaluation.get("recommendation"), evaluation.get("overview", {}).get("one_line_takeaway", "")],
                "method": "综合强信号、风险项、JD 缺口与样本充分度，给出推荐结论与后续建议。",
                "output": evaluation.get("overall_judgment", {}).get("bottom_line", ""),
            },
        ]

    def _build_jd_match_report(self, evaluation: dict) -> dict:
        dimension_reports = evaluation.get("dimension_reports") or []
        dimension_by_name = {item.get("dimension_name"): item for item in dimension_reports if item.get("dimension_name")}
        jd_requirements = self._extract_jd_requirements(evaluation)

        matched = []
        gaps = []
        for req in jd_requirements:
            related = self._match_requirement_to_dimension(req["requirement"], dimension_reports)
            if related:
                level = related.get("signal_level", "待验证")
                entry = {
                    "requirement": req["requirement"],
                    "source": req["source"],
                    "match_level": self._convert_signal_to_match_level(level),
                    "judgment": related.get("judgment", ""),
                    "reasoning": related.get("reasoning", ""),
                    "evidence": related.get("evidence") or [],
                }
                if level in {"强信号", "有信号"}:
                    matched.append(entry)
                else:
                    gaps.append({
                        **entry,
                        "gap_level": "待补证据" if level == "待验证" else "明显短板",
                        "basis": related.get("blind_spot") or related.get("judgment") or "当前没有足够证据支撑该 JD 要求。",
                        "suggestion": f"继续围绕“{req['requirement']}”补充行为案例或真实场景追问。",
                    })
            else:
                gaps.append({
                    "requirement": req["requirement"],
                    "source": req["source"],
                    "match_level": "未匹配",
                    "gap_level": "信息缺失",
                    "judgment": "当前评估结果里没有找到与该 JD 要求直接对应的能力信号。",
                    "reasoning": "这不一定代表候选人不具备该能力，更可能是本场题目没有打到这个点。",
                    "basis": "缺少对应维度或有效面试证据。",
                    "evidence": [],
                    "suggestion": f"针对“{req['requirement']}”补一题要求候选人讲具体经历、动作和结果。",
                })

        risk_constraints = []
        for risk in evaluation.get("risks") or []:
            risk_constraints.append({
                "risk": risk.get("title", ""),
                "severity": risk.get("severity", "中"),
                "description": risk.get("description", ""),
                "evidence": risk.get("evidence") or [],
            })

        return {
            "position_title": evaluation.get("overview", {}).get("position_title", "未知岗位"),
            "summary": self._build_jd_summary(matched, gaps),
            "matched_requirements": matched[:10],
            "gap_requirements": gaps[:10],
            "risk_constraints": risk_constraints[:6],
        }

    def _build_overall_report(self, evaluation: dict) -> dict:
        overview = evaluation.get("overview") or {}
        overall = evaluation.get("overall_judgment") or {}
        jd_report = evaluation.get("jd_match_report") or {}
        lines = []
        lines.append(f"候选人：{overview.get('candidate_name', '未知')}")
        lines.append(f"岗位：{overview.get('position_title', '未知岗位')}")
        lines.append("")
        lines.append("一、整体结论")
        lines.append(overview.get("one_line_takeaway") or "暂无整体结论。")
        if overall.get("bottom_line"):
            lines.append(overall["bottom_line"])
        if evaluation.get("recommendation"):
            lines.append(f"推荐结论：{evaluation['recommendation']}")
        lines.append("")
        lines.append("二、为什么判断他具备这些能力")
        for item in (evaluation.get("dimension_reports") or [])[:8]:
            evidence_desc = self._render_evidence_chain(item.get("evidence") or [])
            lines.append(f"- {item.get('dimension_name', '未命名维度')}：{item.get('judgment', '')}")
            if item.get("reasoning"):
                lines.append(f"  分析过程：{item['reasoning']}")
            if evidence_desc:
                lines.append(f"  证据链：{evidence_desc}")
        lines.append("")
        lines.append("三、结合 JD 的匹配情况")
        if jd_report.get("matched_requirements"):
            for item in jd_report["matched_requirements"][:6]:
                lines.append(f"- 已匹配：{item.get('requirement', '')}。依据：{item.get('judgment', '')}")
        else:
            lines.append("- 当前还没有足够强的 JD 匹配项。")
        lines.append("")
        lines.append("四、存在的不足与依据")
        if jd_report.get("gap_requirements"):
            for item in jd_report["gap_requirements"][:6]:
                lines.append(f"- 不足：{item.get('requirement', '')}")
                lines.append(f"  原因：{item.get('basis') or item.get('judgment') or '证据不足'}")
                evidence_desc = self._render_evidence_chain(item.get("evidence") or [])
                if evidence_desc:
                    lines.append(f"  依据：{evidence_desc}")
        else:
            lines.append("- 暂未识别到明确不足，但仍需结合后续验证。")
        lines.append("")
        lines.append("五、后续建议")
        for suggestion in (evaluation.get("system_feedback") or {}).get("question_design_suggestions") or []:
            lines.append(f"- {suggestion}")

        return {
            "title": f"{overview.get('candidate_name', '候选人')}整体评价报告",
            "summary": overview.get("one_line_takeaway", ""),
            "markdown": "\n".join(lines),
        }

    def _collect_analysis_inputs(self, items: list[Any], key: str | None = None, max_items: int = 6) -> list[str]:
        results = []
        for item in items[:max_items]:
            if isinstance(item, dict) and key:
                value = item.get(key)
            else:
                value = item
            text = str(value or "").strip()
            if text:
                results.append(text)
        return results

    def _extract_jd_requirements(self, evaluation: dict) -> list[dict]:
        requirements = []
        seen = set()
        for item in evaluation.get("dimension_reports") or []:
            name = (item.get("dimension_name") or "").strip()
            category = (item.get("category") or "").strip()
            if not name or name in seen:
                continue
            seen.add(name)
            if category in {"风险画像"}:
                continue
            source = "JD核心要求" if category in {"必须验证", "岗位能力"} else f"岗位画像/{category}"
            requirements.append({"requirement": name, "source": source})
        return requirements

    def _match_requirement_to_dimension(self, requirement: str, dimension_reports: list[dict]) -> dict | None:
        req_keywords = set(self._extract_keywords(requirement))
        best = None
        best_score = 0
        for item in dimension_reports:
            text = " ".join([
                item.get("dimension_name", ""),
                item.get("category", ""),
                item.get("criteria", ""),
                item.get("judgment", ""),
            ])
            score = self._score_keywords(text, list(req_keywords))
            if score > best_score:
                best_score = score
                best = item
        if best_score <= 0:
            return None
        return best

    def _convert_signal_to_match_level(self, level: str) -> str:
        if level == "强信号":
            return "已匹配"
        if level == "有信号":
            return "部分匹配"
        if level == "风险信号":
            return "存在风险"
        return "待验证"

    def _build_jd_summary(self, matched: list[dict], gaps: list[dict]) -> str:
        if matched and not gaps:
            return "候选人与 JD 的主要要求整体一致，当前差距较小。"
        if matched and gaps:
            return "候选人已经匹配部分 JD 核心要求，但仍有若干关键项停留在待验证或存在明显差距。"
        return "当前还没有建立起足够强的 JD 匹配面，主要问题是证据不足或关键要求未被验证。"

    def _render_evidence_chain(self, evidence: list[dict]) -> str:
        parts = []
        for item in evidence[:3]:
            quote = item.get("quote", "")
            turn = item.get("turn_index")
            question = item.get("question", "")
            if quote:
                if question:
                    parts.append(f"[#{turn}] 针对“{question}”回答“{quote}”")
                else:
                    parts.append(f"[#{turn}] “{quote}”")
        return "；".join(parts)

    def _format_turn_for_prompt(self, turn: dict) -> str:
        question_part = f" | 问题={turn['question_text']}" if turn.get("question_text") else ""
        return f"[{turn['turn_index']}] {turn['speaker']}{question_part} | 内容={turn['text']}"

    def _is_usable_llm_evaluation(self, evaluation: dict, transcript: list[dict]) -> bool:
        candidate_turns = [turn for turn in transcript if turn["speaker"] == "候选人" and turn["text"]]
        dimension_reports = evaluation.get("dimension_reports") or []
        evidence_count = sum(len(item.get("evidence") or []) for item in dimension_reports)
        if not dimension_reports:
            return False
        if candidate_turns and evidence_count == 0:
            return False
        if len(candidate_turns) >= 2 and evidence_count < 2:
            return False
        return True

    def _merge_llm_overlay(self, base: dict, llm_eval: dict) -> dict:
        merged = dict(base)
        if llm_eval.get("strengths"):
            merged["strengths"] = llm_eval["strengths"]
        if llm_eval.get("weaknesses"):
            merged["weaknesses"] = llm_eval["weaknesses"]
        if any(item.get("evidence") for item in llm_eval.get("unexpected_signals") or []):
            merged["unexpected_signals"] = llm_eval["unexpected_signals"]
        if any(item.get("evidence") for item in llm_eval.get("risks") or []):
            merged["risks"] = llm_eval["risks"]

        llm_dim_map = {
            (item.get("category"), item.get("dimension_name")): item
            for item in llm_eval.get("dimension_reports") or []
            if item.get("dimension_name")
        }
        merged_dimensions = []
        for base_item in base.get("dimension_reports") or []:
            llm_item = llm_dim_map.get((base_item.get("category"), base_item.get("dimension_name")))
            if llm_item and (llm_item.get("evidence") or []):
                merged_dimensions.append({
                    **base_item,
                    "signal_level": llm_item.get("signal_level") or base_item.get("signal_level"),
                    "judgment": llm_item.get("judgment") or base_item.get("judgment"),
                    "reasoning": llm_item.get("reasoning") or base_item.get("reasoning"),
                    "blind_spot": llm_item.get("blind_spot") or base_item.get("blind_spot"),
                    "evidence": llm_item.get("evidence") or base_item.get("evidence"),
                })
            else:
                merged_dimensions.append(base_item)
        merged["dimension_reports"] = merged_dimensions

        llm_feedback = llm_eval.get("system_feedback") or {}
        base_feedback = base.get("system_feedback") or {}
        merged["system_feedback"] = {
            "signal_sufficient_dimensions": llm_feedback.get("signal_sufficient_dimensions") or base_feedback.get("signal_sufficient_dimensions") or [],
            "signal_insufficient_dimensions": llm_feedback.get("signal_insufficient_dimensions") or base_feedback.get("signal_insufficient_dimensions") or [],
            "question_design_suggestions": llm_feedback.get("question_design_suggestions") or base_feedback.get("question_design_suggestions") or [],
        }
        return merged

    def _extract_keywords(self, text: str) -> list[str]:
        chunks = re.findall(r"[A-Za-z0-9]{2,}|[\u4e00-\u9fff]{2,6}", text or "")
        stop_words = {"能力", "维度", "问题", "说明", "要求", "以及", "相关", "进行", "可以", "这个", "候选人"}
        keywords = []
        for chunk in chunks:
            if chunk in stop_words:
                continue
            keywords.append(chunk)
            if len(chunk) >= 4 and re.fullmatch(r"[\u4e00-\u9fff]+", chunk):
                keywords.append(chunk[:2])
        deduped = []
        seen = set()
        for keyword in keywords:
            if keyword not in seen:
                seen.add(keyword)
                deduped.append(keyword)
        return deduped[:16]

    def _score_keywords(self, text: str, keywords: list[str]) -> int:
        return sum(1 for keyword in keywords if keyword and keyword in text)

    def _contains_risk_phrase(self, text: str) -> bool:
        return any(phrase in text for phrase in RISK_PHRASES)

    def _truncate(self, text: str, limit: int) -> str:
        text = (text or "").strip()
        return text if len(text) <= limit else text[: limit - 1] + "…"
