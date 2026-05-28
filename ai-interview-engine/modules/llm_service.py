"""
大语言模型服务抽象层
支持 OpenAI 兼容接口（OpenAI / DeepSeek / Moonshot / Azure 等）
未配置 LLM 时自动降级为模板方案
"""

import json
import os
import re
from typing import Optional


# ==================== 配置管理 ====================

class LLMConfig:
    """LLM 配置（从环境变量读取）"""

    @staticmethod
    def from_env() -> dict:
        """从环境变量加载配置"""
        return {
            "provider": os.getenv("LLM_PROVIDER", "openai"),
            "api_key": os.getenv("LLM_API_KEY", ""),
            "base_url": os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
            "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
            "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
            "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "2048")),
        }

    @staticmethod
    def validate(config: dict) -> str:
        """验证配置，返回错误信息（空串表示有效）"""
        if not config.get("api_key"):
            return "未配置 API Key"
        if not config.get("base_url"):
            return "未配置 API 地址"
        return ""

    @staticmethod
    def save_to_file(config: dict, filepath: str = None):
        """保存配置到文件"""
        if filepath is None:
            filepath = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), ".env.json"
            )
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    @staticmethod
    def load_from_file(filepath: str = None) -> dict:
        """从文件加载配置"""
        if filepath is None:
            filepath = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), ".env.json"
            )
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return LLMConfig.from_env()


# ==================== LLM 服务 ====================

class LLMService:
    """大语言模型服务"""

    def __init__(self, config: dict = None):
        self._config = config or LLMConfig.from_env()
        self._available = len(LLMConfig.validate(self._config)) == 0
        self._client = None
        if self._available:
            self._init_client()

    def _init_client(self):
        """初始化 OpenAI 客户端"""
        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self._config["api_key"],
                base_url=self._config["base_url"],
            )
        except ImportError:
            self._available = False

    # ==================== 通用调用 ====================

    def chat(self, messages: list, system_prompt: str = None, **kwargs) -> Optional[str]:
        """
        通用聊天接口

        Args:
            messages: 对话消息列表 [{"role": "user", "content": "..."}]
            system_prompt: 系统提示词
            **kwargs: 覆盖默认参数

        Returns:
            模型回复文本，失败返回 None
        """
        if not self._available or not self._client:
            return None

        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        try:
            resp = self._client.chat.completions.create(
                model=kwargs.get("model", self._config["model"]),
                messages=full_messages,
                temperature=kwargs.get("temperature", self._config["temperature"]),
                max_tokens=kwargs.get("max_tokens", self._config["max_tokens"]),
            )
            return resp.choices[0].message.content
        except Exception as e:
            print(f"[LLM Error] {e}")
            return None

    def chat_json(self, messages: list, system_prompt: str = None, **kwargs) -> Optional[dict]:
        """
        调用 LLM 并解析 JSON 返回

        Returns:
            解析后的 dict，失败返回 None
        """
        result = self.chat(messages, system_prompt=system_prompt, **kwargs)
        if not result:
            return None
        return self._extract_json(result)

    def _extract_json(self, text: str) -> Optional[dict]:
        """从文本中提取 JSON"""
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # 尝试从 ```json ``` 代码块提取
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return None

    # ==================== 面试专用方法 ====================

    def generate_questions(
        self, profile: dict, candidate: dict = None, section: str = "技术考察", count: int = 5
    ) -> Optional[list]:
        """
        用 LLM 生成面试问题

        Args:
            profile: 人才画像
            candidate: 候选人档案（可选）
            section: 面试环节名称
            count: 生成问题数

        Returns:
            问题列表，失败返回 None
        """
        position = profile.get("position", {}).get("title", "未知岗位")
        skills = profile.get("requirements", {}).get("skills", [])

        system_prompt = """你是一位专业的面试官，擅长根据岗位要求和候选人背景设计高质量的面试问题。
请严格按照 JSON 格式返回，格式为：
{
  "questions": [
    {
      "question_text": "问题内容",
      "category": "技术|项目经验|软技能|文化契合|行为",
      "difficulty": "简单|中等|困难",
      "expected_answer_keywords": ["关键词1", "关键词2"],
      "follow_up_triggers": ["触发词1", "触发词2"]
    }
  ]
}
要求：
1. 问题要具体、有深度，能考察候选人的真实水平
2. 避免过于通用或简单的是非题
3. 结合岗位的实际工作场景设计问题"""

        skill_desc = "\n".join([f"- {s['name']}（{s.get('level', '熟悉')}）" for s in skills])
        candidate_info = ""
        if candidate and candidate.get("experiences"):
            exp = candidate["experiences"][0]
            candidate_info = f"\n候选人经历：{exp.get('company', '')} - {exp.get('title', '')}\n{exp.get('description', '')[:200]}"

        user_prompt = f"""我正在面试「{position}」岗位，当前环节是「{section}」。

岗位技能要求：
{skill_desc}
{candidate_info}

请针对上述环节生成 {count} 个高质量的面试问题。"""

        result = self.chat_json(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
        )
        if result and "questions" in result:
            return result["questions"]
        return None

    def generate_follow_up(
        self,
        question: str,
        user_answer: str,
        profile: dict,
        dialogue_history: list = None,
    ) -> Optional[str]:
        """
        用 LLM 判断是否需要追问并生成追问内容

        Args:
            question: 原问题
            user_answer: 候选人回答
            profile: 人才画像
            dialogue_history: 最近对话历史

        Returns:
            追问文本，不需要追问则返回空字符串，失败返回 None
        """
        system_prompt = """你是一位专业的 AI 面试官。你需要根据候选人的回答，判断是否需要追问。

规则：
1. 如果回答很详细、有深度（超过100字且有具体内容），返回 {"follow_up": false}
2. 如果回答比较简短或不够深入，返回 {"follow_up": true, "question": "追问内容"}
3. 追问应该自然、有针对性，而不是简单重复原问题
4. 追问应引导候选人更深入地分享经验和见解

请严格返回 JSON 格式。"""

        history_text = ""
        if dialogue_history:
            recent = [d for d in dialogue_history[-4:] if d["speaker"] == "候选人"]
            if recent:
                history_text = "\n历史回答:\n" + "\n".join(
                    [f"- {d['text'][:100]}" for d in recent]
                )

        user_prompt = f"""岗位：{profile.get('position', {}).get('title', '未知')}

原问题：{question}

候选人的回答：{user_answer}{history_text}

请判断是否需要追问，并给出追问内容。"""

        result = self.chat_json(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
            temperature=0.5,
        )
        if result:
            if result.get("follow_up"):
                return result.get("question", "")
            return ""  # 不需要追问
        return None

    def evaluate_interview(self, interview: dict) -> Optional[dict]:
        """
        用 LLM 对整场面试进行评估

        Args:
            interview: 完整的面试记录

        Returns:
            评估结果 dict
        """
        dialogues = interview.get("dialogues", [])
        if not dialogues:
            return None

        # 构建对话摘要
        transcript = []
        for d in dialogues:
            speaker = "面试官" if d["speaker"] == "AI" else "候选人"
            transcript.append(f"{speaker}：{d['text']}")

        system_prompt = """你是一位资深的招聘专家。请你根据面试记录，对候选人进行全面评估。

请严格按照以下 JSON 格式返回评估结果：
{
  "overall_score": 0-100,
  "dimension_scores": {
    "技术能力": 0-100,
    "项目经验": 0-100,
    "沟通表达": 0-100,
    "文化契合": 0-100
  },
  "strengths": ["优势1", "优势2", "优势3"],
  "weaknesses": ["不足1", "不足2"],
  "recommendation": "强烈推荐|推荐|待定|不推荐",
  "ai_comment": "综合评价意见，300字以内"
}

评分标准：
- 90-100: 超出预期，强烈推荐
- 75-89: 符合要求，推荐
- 60-74: 基本符合，待定
- <60: 不符合要求，不推荐"""

        transcript_text = "\n".join(transcript)
        position_name = interview.get('candidate', {}).get('profile_ref', '未知')
        user_prompt = f"""以下是本次面试的完整记录，请进行评估：

{transcript_text}

岗位：{position_name}"""

        result = self.chat_json(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=1500,
        )
        return result

    @property
    def is_available(self) -> bool:
        """LLM 是否可用"""
        return self._available

    def get_config(self) -> dict:
        """获取当前配置（隐藏 API Key）"""
        cfg = dict(self._config)
        if cfg.get("api_key"):
            cfg["api_key"] = cfg["api_key"][:8] + "..." + cfg["api_key"][-4:]
        return {**cfg, "available": self._available}

    def update_config(self, config: dict):
        """更新配置"""
        self._config.update(config)
        self._available = len(LLMConfig.validate(self._config)) == 0
        if self._available:
            self._init_client()
        else:
            self._client = None


# ==================== 便捷函数 ====================

_service_instance = None


def get_llm_service() -> LLMService:
    """获取全局 LLM 服务实例"""
    global _service_instance
    if _service_instance is None:
        config = LLMConfig.load_from_file()
        _service_instance = LLMService(config)
    return _service_instance


def reload_llm_service(config: dict = None):
    """重新加载 LLM 服务"""
    global _service_instance
    if config:
        LLMConfig.save_to_file(config)
    _service_instance = LLMService(config or LLMConfig.load_from_file())
    return _service_instance
