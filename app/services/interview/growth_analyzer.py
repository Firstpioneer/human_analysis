"""
成长性分析器 — 从画像和简历中推理候选人的成长潜力

核心思想：
  避免"量化打分"，而是从以下维度推理成长性：
  1. 学习轨迹 — 技能宽度 vs 深度的变化趋势
  2. 挑战偏好 — 是否主动选择有难度的项目/岗位
  3. 适应能力 — 跨技术栈/跨行业的迁移经验
  4. 成长速度 — 同等年限内的职级跃迁速度
  5. 自驱力 — 是否有开源贡献、技术博客等额外信号
"""
import json
from typing import Optional

from .llm_service import get_llm_service


class GrowthAnalyzer:
    """成长性分析器"""

    def __init__(self, use_llm: bool = True):
        self._use_llm = use_llm

    def analyze_growth(self, profile: dict, candidate: Optional[dict] = None) -> dict:
        """
        分析候选人的成长潜力（非量化评估）

        返回包含以下维度的分析结果：
        - growth_trajectory: 成长轨迹描述
        - learning_ability: 学习能力评估
        - challenge_preference: 挑战偏好
        - adaptability: 适应能力
        - potential_concerns: 潜在风险
        - overall_assessment: 综合成长性判断
        """
        if not self._use_llm:
            return self._default_analysis()

        llm = get_llm_service()
        if not llm or not llm.is_available:
            return self._default_analysis()

        try:
            result = llm.chat_json(
                messages=[{"role": "user", "content": self._build_analysis_prompt(profile, candidate)}],
                system_prompt=self._get_system_prompt(),
                temperature=0.4,
                max_tokens=2000,
            )
            if result:
                return result
        except Exception:
            pass
        return self._default_analysis()

    def _get_system_prompt(self) -> str:
        return """你是一位资深的人才发展顾问，擅长从非量化角度评估候选人的成长潜力。

请根据岗位画像和候选人信息，分析以下维度：

1. **成长轨迹 (growth_trajectory)**：候选人技能从单一到多元/从浅到深的变化路径
2. **学习能力 (learning_ability)**：通过技术栈变化、跨领域经验判断学习速度
3. **挑战偏好 (challenge_preference)**：是否主动选择有难度的任务或新领域
4. **适应能力 (adaptability)**：面对变化（技术转型、行业切换）的适应表现
5. **成长信号 (growth_signals)**：开源贡献、技术博客、专利等额外自驱力证据
6. **潜在风险 (potential_concerns)**：可能限制成长的瓶颈或盲点
7. **综合评估 (overall_assessment)**：成长性的定性结论

⚠️ 重要：不要给出具体分数！用描述性语言，例如"成长潜力较高"、"学习能力强"等。

请按以下 JSON 格式返回：
{
  "growth_trajectory": "描述",
  "learning_ability": "描述",
  "challenge_preference": "描述",
  "adaptability": "描述",
  "growth_signals": ["信号1", "信号2"],
  "potential_concerns": ["风险1", "风险2"],
  "overall_assessment": "综合描述"
}"""

    def _build_analysis_prompt(self, profile: dict, candidate: Optional[dict]) -> str:
        position = profile.get("position", {})
        req = profile.get("requirements", {})
        skills = req.get("skills", [])
        signal_dims = profile.get("_signal_dimensions", [])

        prompt = f"【岗位画像】\n岗位：{position.get('title', '未知')}\n"

        if skills:
            prompt += "\n期望技能：\n"
            for s in skills:
                prompt += f"- {s.get('name')}（{s.get('level', '熟悉')}）\n"

        if signal_dims:
            prompt += "\n画像维度信号：\n"
            for cat in signal_dims:
                for dim in cat.get("dimensions", []):
                    prompt += f"- {dim.get('name', '')}：{dim.get('description', '')}\n"

        if candidate:
            prompt += f"\n【候选人信息】\n姓名：{candidate.get('name', '未知')}\n"
            prompt += f"概述：{candidate.get('summary', '无')}\n"

            for exp in candidate.get("experiences", []):
                prompt += (
                    f"\n工作经验：{exp.get('company', '')} | {exp.get('title', '')} | "
                    f"{exp.get('start_date', '')} - {exp.get('end_date', '至今')}\n"
                )
                prompt += f"  描述：{exp.get('description', '')}\n"

            edu = candidate.get("education", [])
            if edu:
                prompt += "\n教育背景：\n"
                for e in edu:
                    prompt += f"- {e.get('school', '')} {e.get('degree', '')} {e.get('major', '')}\n"

            ext = candidate.get("external_profiles", {})
            if ext:
                prompt += "\n外部信号：\n"
                for k, v in ext.items():
                    prompt += f"- {k}：{v}\n"

        prompt += "\n请分析这位候选人的成长潜力，重点关注其发展轨迹和未来可能达到的高度。"
        return prompt

    def _default_analysis(self) -> dict:
        return {
            "growth_trajectory": "信息不足以分析成长轨迹",
            "learning_ability": "需要更多数据评估",
            "challenge_preference": "需面试验证",
            "adaptability": "需面试验证",
            "growth_signals": [],
            "potential_concerns": [],
            "overall_assessment": "建议在面试中进一步了解候选人的成长经历和发展规划",
        }
