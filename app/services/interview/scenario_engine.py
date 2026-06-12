"""
需求场景引擎 — 基于公司需求筛选匹配的候选人画像

核心概念：
  1. 公司定义"需求场景"（如：团队缺前端架构能力）
  2. 场景包含：缺失能力维度、期望水平、团队现状
  3. 引擎将场景与候选人画像进行匹配，生成面试关注点
  4. 面试围绕这些关注点展开，最终验证候选人是否满足需求
"""
from typing import Optional


# ── 预定义场景模板 ──

BUILTIN_SCENARIOS = [
    {
        "id": "tech_deepening",
        "title": "技术深耕",
        "description": "团队在某一技术领域深度不足，需要该领域专家带领突破",
        "focus": "技术深度与架构能力",
        "example": "前端团队缺少架构能力，需要一名能搭建组件库和构建工具链的高级前端工程师",
    },
    {
        "id": "tech_expansion",
        "title": "技术拓展",
        "description": "团队需要拓展新技术栈，寻找有相关转型经验的人才",
        "focus": "学习能力与技术广度",
        "example": "后端团队准备引入 Go 语言，需要一名有 Python 转 Go 经验的工程师",
    },
    {
        "id": "team_lead",
        "title": "团队管理",
        "description": "现有团队缺少技术 leader，需要具备管理能力的技术负责人",
        "focus": "领导力与团队协作",
        "example": "小组缺少技术负责人，需要一名能带 5-8 人小组的资深工程师",
    },
    {
        "id": "quality_improvement",
        "title": "质量提升",
        "description": "项目质量亟待提升，需要测试/工程化方面的人才",
        "focus": "工程化与质量意识",
        "example": "项目缺少自动化测试和 CI/CD 流程，需要一名 DevOps 或质量保障工程师",
    },
    {
        "id": "business_innovation",
        "title": "业务创新",
        "description": "团队需要开拓新业务方向，寻找有创新思维和业务敏感度的人才",
        "focus": "业务理解与创新能力",
        "example": "公司准备进军教育领域，需要一名有教育行业经验的产品/技术人才",
    },
]


class ScenarioEngine:
    """需求场景引擎"""

    @staticmethod
    def get_builtin_scenarios() -> list:
        return BUILTIN_SCENARIOS

    @staticmethod
    def build_scenario_prompt(scenario: dict, profile: dict, candidate: Optional[dict] = None) -> str:
        """根据场景和画像，生成场景化的面试关注点提示"""
        scenario_title = scenario.get("title", "")
        scenario_desc = scenario.get("description", "")
        scenario_focus = scenario.get("focus", "")
        scenario_example = scenario.get("example", "")

        position = profile.get("position", {})
        title = position.get("title", "未知岗位")
        req = profile.get("requirements", {})
        skills = req.get("skills", [])
        soft_skills = req.get("soft_skills", [])

        # 从画像中提取信号维度
        signal_dims = profile.get("_signal_dimensions", [])
        must_have = profile.get("_must_have", [])
        anti_profile = profile.get("_anti_profile", [])

        prompt_parts = [
            f"## 需求场景",
            f"场景类型：{scenario_title}",
            f"场景描述：{scenario_desc}",
            f"考察重点：{scenario_focus}",
            f"典型情境：{scenario_example}",
            "",
            f"## 招聘岗位",
            f"岗位名称：{title}",
        ]

        if skills:
            prompt_parts.append("\n【技能要求】")
            for s in skills:
                prompt_parts.append(f"- {s.get('name')}（{s.get('level', '熟悉')}，权重{s.get('weight', 5)}）")

        if soft_skills:
            prompt_parts.append("\n【软技能】\n" + "\n".join(f"- {s}" for s in soft_skills))

        if signal_dims:
            prompt_parts.append("\n【画像信号维度】")
            for category in signal_dims:
                prompt_parts.append(f"\n{category.get('category', '')}")
                for dim in category.get("dimensions", []):
                    prompt_parts.append(f"  · {dim.get('name', '')}（{dim.get('weight', '')}）：{dim.get('description', '')}")

        if must_have:
            prompt_parts.append("\n【必须验证】\n" + "\n".join(f"- {s}" for s in must_have))

        if anti_profile:
            prompt_parts.append("\n【风险信号】\n" + "\n".join(f"- {s}" for s in anti_profile))

        if candidate:
            prompt_parts.extend([
                "",
                f"## 候选人信息",
                f"姓名：{candidate.get('name', '未知')}",
                f"概述：{candidate.get('summary', '无')}",
            ])
            for exp in candidate.get("experiences", []):
                prompt_parts.append(
                    f"- {exp.get('company', '')} {exp.get('title', '')} "
                    f"（{exp.get('start_date', '')} - {exp.get('end_date', '至今')}）"
                )

        return "\n".join(prompt_parts)
