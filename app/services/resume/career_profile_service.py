"""职业画像标准化服务"""
import json
import logging
import re

import config


class CareerProfileService:
    """将 HR 输入的职业要求归一化为岗位推荐可消费的结构。"""

    def __init__(self):
        self._api_key = config.RESUME_LLM_API_KEY
        self._base_url = config.RESUME_LLM_BASE_URL
        self._model = config.RESUME_LLM_MODEL
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if not self._api_key:
                raise RuntimeError("未配置 RESUME_LLM_API_KEY，无法调用职业画像标准化服务")
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._client

    def normalize_requirement(self, requirement_text: str) -> dict:
        text = requirement_text.strip()
        if not text:
            raise ValueError("职业要求不能为空")
        if not self._api_key:
            return self._heuristic_profile(text)

        prompt = f"""
请将以下 HR 输入的职业/岗位要求整理为统一职业画像 JSON。

【HR 输入】
{text}

【输出格式】
{{
  "title": "岗位名称",
  "department": "部门，无法判断则为空字符串",
  "seniority": "实习/初级/中级/高级/专家/负责人/不限",
  "responsibilities": ["核心职责1", "核心职责2"],
  "must_have": ["必要条件1", "必要条件2"],
  "nice_to_have": ["加分项1", "加分项2"],
  "skill_keywords": ["技能关键词1", "技能关键词2"],
  "growth_expectations": ["该岗位期待的成长性信号1", "该岗位期待的成长性信号2"],
  "profile_dimensions": [
    {{
      "key": "维度英文或拼音key",
      "preferred_direction": "偏好的候选人倾向",
      "weight": "核心/重要/参考",
      "description": "这个维度如何判断匹配"
    }}
  ],
  "anti_profile": ["明显不适合画像1"],
  "summary": "80字以内总结"
}}

要求：
1. 只输出纯 JSON，不要 Markdown。
2. skill_keywords 只放可用于匹配简历的关键词，最多12个。
3. growth_expectations 要描述可从简历推断的成长潜力信号，例如学习迁移、复杂问题处理、主动推进、复盘迭代、责任范围扩大。
"""
        messages = [
            {"role": "system", "content": "你是一个严谨的招聘岗位画像标准化助手，只输出 JSON。"},
            {"role": "user", "content": prompt},
        ]
        try:
            completion = self.client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.2,
                max_tokens=1800,
            )
            content = completion.choices[0].message.content or ""
            parsed = json.loads(self._extract_json(content))
            return self._normalize_profile(parsed, text, source="llm")
        except Exception as exc:
            logging.error("职业画像标准化失败，使用本地规则回退: %s", exc)
            return self._heuristic_profile(text)

    def _extract_json(self, text: str) -> str:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        return match.group(0) if match else text

    def _normalize_profile(self, profile: dict, raw_text: str, source: str) -> dict:
        if not isinstance(profile, dict):
            profile = {}

        def as_list(value, limit=8):
            if isinstance(value, str):
                value = [item.strip() for item in re.split(r"[,，、；;\n]", value) if item.strip()]
            if not isinstance(value, list):
                value = []
            return [str(item).strip()[:80] for item in value if str(item).strip()][:limit]

        dimensions = []
        for dim in profile.get("profile_dimensions", []) or []:
            if not isinstance(dim, dict):
                continue
            dimensions.append({
                "key": str(dim.get("key") or "")[:40],
                "preferred_direction": str(dim.get("preferred_direction") or "")[:80],
                "weight": str(dim.get("weight") or "参考")[:10],
                "description": str(dim.get("description") or "")[:160],
            })

        title = str(profile.get("title") or "").strip() or self._guess_title(raw_text)
        skill_keywords = as_list(profile.get("skill_keywords"), limit=12)
        if not skill_keywords:
            skill_keywords = self._extract_keywords(raw_text)
        return {
            "title": title[:60] or "未命名岗位",
            "department": str(profile.get("department") or "")[:60],
            "seniority": str(profile.get("seniority") or "不限")[:20],
            "responsibilities": as_list(profile.get("responsibilities"), limit=8),
            "must_have": as_list(profile.get("must_have"), limit=10),
            "nice_to_have": as_list(profile.get("nice_to_have"), limit=10),
            "skill_keywords": skill_keywords[:12],
            "growth_expectations": as_list(profile.get("growth_expectations"), limit=6) or [
                "能从项目中体现学习迁移、主动推进和复盘迭代能力"
            ],
            "profile_dimensions": dimensions[:8],
            "anti_profile": as_list(profile.get("anti_profile"), limit=6),
            "summary": str(profile.get("summary") or raw_text[:80])[:120],
            "raw_requirement": raw_text,
            "normalized_by": source,
        }

    def _heuristic_profile(self, text: str) -> dict:
        title = self._guess_title(text)
        lines = [line.strip(" -•\t") for line in text.splitlines() if line.strip()]
        responsibilities = [line for line in lines if any(k in line for k in ("负责", "职责", "完成", "建设", "开发", "推进"))][:6]
        must_have = [line for line in lines if any(k in line for k in ("要求", "必须", "熟悉", "掌握", "经验", "能力"))][:8]
        profile = {
            "title": title,
            "department": "",
            "seniority": self._guess_seniority(text),
            "responsibilities": responsibilities,
            "must_have": must_have,
            "nice_to_have": [line for line in lines if any(k in line for k in ("加分", "优先", "更佳"))][:6],
            "skill_keywords": self._extract_keywords(text),
            "growth_expectations": [
                "能快速学习岗位相关技术或业务",
                "能在复杂任务中主动推进并复盘优化",
            ],
            "profile_dimensions": [
                {
                    "key": "growth_potential",
                    "preferred_direction": "学习迁移强、主动负责、能复盘迭代",
                    "weight": "重要",
                    "description": "从项目难度、职责变化、结果指标和迭代痕迹判断成长性。",
                }
            ],
            "anti_profile": [],
            "summary": text[:100],
        }
        return self._normalize_profile(profile, text, source="heuristic")

    def _guess_title(self, text: str) -> str:
        patterns = [
            r"(?:岗位名称|职位名称|招聘岗位|职位|岗位)[:：]\s*([\u4e00-\u9fa5A-Za-z0-9/+\- ]{2,40})",
            r"^([\u4e00-\u9fa5A-Za-z0-9/+\- ]{2,40}(?:工程师|开发|产品经理|设计师|运营|专员|负责人|实习生))",
        ]
        for pattern in patterns:
            match = re.search(pattern, text.strip())
            if match:
                return match.group(1).strip(" ，,。；;")
        first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
        return first_line[:30] or "未命名岗位"

    def _guess_seniority(self, text: str) -> str:
        for level in ("实习", "初级", "中级", "高级", "资深", "专家", "负责人"):
            if level in text:
                return "高级" if level == "资深" else level
        return "不限"

    def _extract_keywords(self, text: str) -> list[str]:
        known = [
            "Python", "Java", "Go", "C++", "JavaScript", "TypeScript", "Vue", "React",
            "Node.js", "FastAPI", "Django", "Flask", "Spring", "MySQL", "PostgreSQL",
            "Redis", "MongoDB", "Docker", "Kubernetes", "Linux", "Nginx", "PyTorch",
            "TensorFlow", "LLM", "RAG", "OCR", "数据分析", "机器学习", "深度学习",
            "产品设计", "项目管理", "沟通协调", "招聘", "培训", "用户研究",
            "嵌入式", "STM32", "FPGA", "PCB",
        ]
        found = []
        lower = text.lower()
        for keyword in known:
            if keyword.lower() in lower and keyword not in found:
                found.append(keyword)
        return found[:12]
