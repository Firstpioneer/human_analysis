"""面试问题方案自动生成模块（验证计划版）"""
import json
from typing import Optional

from .llm_service import get_llm_service


class QuestionGenerator:
    def __init__(self, use_llm: bool = True):
        self._use_llm = use_llm

    def _get_llm(self):
        if not self._use_llm:
            return None
        svc = get_llm_service()
        return svc if svc.is_available else None

    def generate_plan(self, profile: dict, candidate: Optional[dict] = None,
                      total_duration_minutes: int = 45) -> dict:
        if not profile:
            raise ValueError("人才画像不能为空")
        llm = self._get_llm()
        if not llm:
            raise RuntimeError(
                "未检测到大语言模型配置。"
                "请在页面底部「大语言模型配置」面板中填写 API Key 后重试。"
            )
        plan = self._generate_with_llm(llm, profile, candidate, total_duration_minutes)
        if not plan:
            raise RuntimeError("大语言模型生成面试方案失败，请检查 API 配置或稍后重试。")
        return {**plan, "_generated_by": "llm"}

    def _generate_with_llm(self, llm, profile, candidate, total_minutes):
        position = profile.get("position", {}).get("title", "未知岗位")
        department = profile.get("position", {}).get("department", "")
        level = profile.get("position", {}).get("level", "")
        salary = profile.get("position", {}).get("salary_range", "")
        req = profile.get("requirements", {})
        edu = req.get("education", {})
        exp_req = req.get("experience", {})
        skills = req.get("skills", [])
        soft_skills_list = req.get("soft_skills", [])
        qualifications = profile.get("qualifications", {})
        culture = profile.get("culture_fit", {})

        position_context = f"""岗位名称：{position}
部门：{department}
职级：{level}
薪资范围：{salary}

【教育要求】
最低学历：{edu.get('min_degree', '不限')}
优先专业：{', '.join(edu.get('preferred_majors', [])) or '不限'}

【经验要求】
最低年限：{exp_req.get('min_years', '不限')}年
优先行业：{', '.join(exp_req.get('preferred_industries', [])) or '不限'}

【技能要求】"""
        for s in skills:
            position_context += f"\n- {s['name']}（{s.get('level', '熟悉')}，权重{s.get('weight', 5)}）"
        if soft_skills_list:
            position_context += f"\n\n【软技能要求】\n" + "\n".join(f"- {s}" for s in soft_skills_list)
        certs = qualifications.get('certifications', [])
        projects = qualifications.get('projects', [])
        other = qualifications.get('other', [])
        if certs or projects or other:
            position_context += "\n\n【加分项】"
            if certs:
                position_context += "\n证书：" + ", ".join(certs)
            if projects:
                position_context += "\n项目经验要求：" + ", ".join(projects)
            if other:
                position_context += "\n其他：" + ", ".join(other)
        if culture:
            position_context += f"\n\n【文化契合】"
            if culture.get('team_size'):
                position_context += f"\n团队规模：{culture['team_size']}"
            if culture.get('work_style'):
                position_context += f"\n工作风格：{culture['work_style']}"
            if culture.get('values'):
                position_context += f"\n价值观：{', '.join(culture['values'])}"

        signal_dimensions = profile.get("_signal_dimensions", [])
        if signal_dimensions:
            position_context += "\n\n【画像信号维度】"
            for category in signal_dimensions:
                position_context += f"\n- {category.get('category', '未分类')}"
                for dim in category.get("dimensions", []):
                    position_context += (
                        f"\n  · {dim.get('name', '')}"
                        f"（{dim.get('weight', '参考')}）：{dim.get('description', '')}"
                    )
        if profile.get("_must_have"):
            position_context += "\n\n【必须验证】\n" + "\n".join(f"- {s}" for s in profile["_must_have"])
        if profile.get("_nice_to_have"):
            position_context += "\n\n【加分信号】\n" + "\n".join(f"- {s}" for s in profile["_nice_to_have"])
        if profile.get("_anti_profile"):
            position_context += "\n\n【风险画像】\n" + "\n".join(f"- {s}" for s in profile["_anti_profile"])
        if profile.get("_general_questions"):
            position_context += "\n\n【画像建议问题】\n" + "\n".join(f"- {s}" for s in profile["_general_questions"])

        candidate_context = ""
        if candidate:
            candidate_context = f"""
【候选人信息】
姓名：{candidate.get('name', '未知')}
概述：{candidate.get('summary', '无')}

工作经历："""
            for exp in candidate.get('experiences', []):
                candidate_context += f"""
- {exp.get('company', '')} | {exp.get('title', '')} | {exp.get('start_date', '')} - {exp.get('end_date', '至今')}
  描述：{exp.get('description', '')}
  亮点：{', '.join(exp.get('highlights', [])) or '无'}"""
            if candidate.get('education'):
                candidate_context += "\n\n教育背景："
                for edu_item in candidate['education']:
                    candidate_context += f"\n- {edu_item.get('school', '')} {edu_item.get('degree', '')} {edu_item.get('major', '')}"
            if candidate.get('skills'):
                candidate_context += "\n\n已有技能："
                for cs in candidate['skills']:
                    candidate_context += f"\n- {cs['name']}（{cs.get('level', '')}）"
            if candidate.get('external_profiles'):
                candidate_context += "\n\n外部信号："
                for key, value in candidate['external_profiles'].items():
                    candidate_context += f"\n- {key}：{value}"
            if candidate.get('_blind_spots'):
                candidate_context += "\n\n简历盲点 / 待澄清："
                for spot in candidate['_blind_spots']:
                    candidate_context += f"\n- {spot}"

        system_prompt = """你是一位资深的技术面试官和招聘专家。请根据提供的岗位要求和候选人信息，设计一份完整的面试方案。

你必须同时输出两部分：验证维度计划 和 面试环节安排。严格按以下 JSON 格式返回，不要包含其他内容：

{
  "verification_dimensions": [
    {
      "dimension_id": "D001",
      "name": "维度名称",
      "category": "技术|项目经验|软技能|文化契合|行为",
      "priority": "must_have|nice_to_have|risk_check",
      "criteria": "这个维度要验证什么，达到什么标准算通过",
      "success_signals": ["回答中出现什么特征说明候选人具备这个能力"],
      "risk_signals": ["回答中出现什么特征说明候选人可能不具备这个能力"],
      "probing_strategies": ["如果回答模糊，应该从哪些角度追问"],
      "planned_questions": [
        {
          "question_text": "问题内容",
          "difficulty": "简单|中等|困难",
          "expected_answer_keywords": ["预期关键词"]
        }
      ],
      "estimated_minutes": 8
    }
  ],
  "sections": [
    {
      "section_name": "环节名称",
      "duration_minutes": 整数,
      "focus_area": "考察重点描述",
      "linked_dimensions": ["D001", "D002"],
      "questions": [
        {
          "question_text": "问题内容",
          "category": "技术|项目经验|软技能|文化契合|行为",
          "difficulty": "简单|中等|困难",
          "expected_answer_keywords": ["预期关键词"],
          "follow_up_triggers": ["具体", "为什么", "结果", "举例", "优化"],
          "linked_dimension": "D001"
        }
      ]
    }
  ]
}

设计原则：
1. 验证维度要精炼，3-6 个核心维度即可，不要超过 8 个
2. 每个维度必须有明确的 criteria（通过标准）、success_signals 和 risk_signals
3. must_have 维度优先分配时间，nice_to_have 可以快速带过
4. probing_strategies 要具体，比如"追问技术选型理由"而不是"深入追问"
5. sections 中的每个 question 必须 linked_dimension 到某个验证维度
6. 问题必须完全根据岗位画像和候选人信息动态设计，不得使用通用模板
7. 技术问题要结合岗位的具体技能要求和工作场景，考察深度而非广度
8. 如果有候选人简历，问题要针对其经历定制，验证其声称的能力
9. 对简历盲点要设计澄清问题，对外部信号可做可信度验证
10. 问题要层层递进：从基础理解 → 实践应用 → 深度思考
11. 面试总时长 {total_minutes} 分钟，请合理分配各环节时间"""

        user_prompt = f"""请为以下岗位设计一份完整的面试方案。

【岗位画像】
{position_context}
{candidate_context}

请生成一场约 {total_minutes} 分钟的完整面试方案，包含验证维度计划和面试环节安排。"""

        result = llm.chat_json(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=4096,
        )
        if not result:
            return None

        sections = result.get("sections", [])
        if not isinstance(sections, list) or len(sections) < 2:
            return None

        # 验证并规范化 sections
        question_id_counter = [0]
        validated_sections = []
        for section in sections:
            questions = section.get("questions", [])
            validated_questions = []
            for q in questions:
                question_id_counter[0] += 1
                validated_questions.append({
                    "question_id": f"Q{question_id_counter[0]:04d}",
                    "question_text": q.get("question_text", ""),
                    "category": q.get("category", "技术"),
                    "difficulty": q.get("difficulty", "中等"),
                    "expected_answer_keywords": q.get("expected_answer_keywords", []),
                    "follow_up_triggers": q.get("follow_up_triggers", ["具体", "为什么", "结果"]),
                    "linked_dimension": q.get("linked_dimension", ""),
                })
            validated_sections.append({
                "section_name": section.get("section_name", "面试环节"),
                "duration_minutes": section.get("duration_minutes", 10),
                "focus_area": section.get("focus_area", ""),
                "linked_dimensions": section.get("linked_dimensions", []),
                "questions": validated_questions,
            })

        has_qna = any("提问" in s["section_name"] for s in validated_sections)
        if not has_qna:
            validated_sections.append({
                "section_name": "候选人提问",
                "duration_minutes": 5,
                "focus_area": "候选人疑问解答",
                "linked_dimensions": [],
                "questions": [],
            })

        # 验证并规范化 verification_dimensions
        raw_dims = result.get("verification_dimensions", [])
        validated_dims = []
        dim_id_map = {}
        if isinstance(raw_dims, list):
            for idx, dim in enumerate(raw_dims):
                dim_id = dim.get("dimension_id") or f"D{idx + 1:03d}"
                dim_id_map[dim_id] = True
                validated_dims.append({
                    "dimension_id": dim_id,
                    "name": dim.get("name", f"维度{idx + 1}"),
                    "category": dim.get("category", "技术"),
                    "priority": dim.get("priority", "nice_to_have"),
                    "criteria": dim.get("criteria", ""),
                    "success_signals": dim.get("success_signals", []),
                    "risk_signals": dim.get("risk_signals", []),
                    "probing_strategies": dim.get("probing_strategies", []),
                    "planned_questions": [
                        {
                            "question_id": pq.get("question_id", ""),
                            "question_text": pq.get("question_text", ""),
                            "difficulty": pq.get("difficulty", "中等"),
                        }
                        for pq in dim.get("planned_questions", [])
                    ],
                    "estimated_minutes": dim.get("estimated_minutes", 5),
                })

        # 如果 LLM 没有生成验证维度，从 sections 的 linked_dimensions 反向构建
        if not validated_dims:
            dim_idx = 0
            seen = set()
            for section in validated_sections:
                for q in section.get("questions", []):
                    lid = q.get("linked_dimension", "")
                    if lid and lid not in seen:
                        seen.add(lid)
                        dim_idx += 1
                        validated_dims.append({
                            "dimension_id": lid,
                            "name": section.get("focus_area", f"维度{dim_idx}"),
                            "category": q.get("category", "技术"),
                            "priority": "must_have" if dim_idx <= 3 else "nice_to_have",
                            "criteria": section.get("focus_area", ""),
                            "success_signals": [],
                            "risk_signals": [],
                            "probing_strategies": [],
                            "planned_questions": [],
                            "estimated_minutes": section.get("duration_minutes", 5),
                        })

        return {
            "total_duration_minutes": total_minutes,
            "sections": validated_sections,
            "verification_dimensions": validated_dims,
        }

    def get_question_by_id(self, plan: dict, question_id: str) -> Optional[dict]:
        for section in plan.get("sections", []):
            for q in section.get("questions", []):
                if q["question_id"] == question_id:
                    return q
        return None
