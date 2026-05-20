from openai import OpenAI
from models import Message
from prompts import AGENT_SYSTEM_PROMPT, JD_PARSE_PROMPT, PROFILE_GENERATE_PROMPT
import json
import re


class RecruitmentAgent:
    def __init__(self, api_key: str):
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        self.model = "deepseek-chat"

    def _call_llm(self, messages: list[dict], temperature: float = 0.7) -> str:
        """调用DeepSeek API"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=4096
        )
        return response.choices[0].message.content

    def _build_context_summary(self, profile_draft: dict | None) -> str:
        """构建当前画像状态的上下文摘要"""
        if not profile_draft:
            return ""
        parts = []
        if profile_draft.get("job_title"):
            parts.append(f"岗位：{profile_draft['job_title']}")
        if profile_draft.get("company_context", {}).get("why_hire"):
            parts.append(f"招聘原因：{profile_draft['company_context']['why_hire']}")
        if profile_draft.get("must_have"):
            parts.append(f"已知必要条件：{', '.join(profile_draft['must_have'])}")
        if profile_draft.get("anti_profile"):
            parts.append(f"已知排除条件：{', '.join(profile_draft['anti_profile'])}")
        if parts:
            return "【当前已收集的画像信息】\n" + "\n".join(parts)
        return ""

    def _compress_old_messages(self, messages: list[Message], max_recent: int = 10) -> list[dict]:
        """压缩对话历史：早期消息压缩为摘要，保留最近N条完整消息"""
        if len(messages) <= max_recent:
            return [{"role": m.role, "content": m.content} for m in messages]

        old_messages = messages[:-max_recent]
        recent_messages = messages[-max_recent:]

        # 构建早期对话摘要
        old_text = "\n".join(
            f"{'招聘方' if m.role == 'user' else '分析师'}：{m.content[:200]}"
            for m in old_messages
        )
        summary_msg = {
            "role": "system",
            "content": f"【早期对话摘要】\n{old_text}\n\n以上是之前的对话要点，请基于此继续对话。"
        }

        result = [summary_msg]
        for m in recent_messages:
            result.append({"role": m.role, "content": m.content})
        return result

    def chat(self, messages: list[Message], profile_draft: dict | None = None) -> str:
        """主对话入口"""
        # 构建系统提示
        system_content = AGENT_SYSTEM_PROMPT
        context_summary = self._build_context_summary(profile_draft)
        if context_summary:
            system_content += f"\n\n{context_summary}"

        # 构建消息列表
        llm_messages = [{"role": "system", "content": system_content}]

        # 压缩历史消息
        compressed = self._compress_old_messages(messages)
        llm_messages.extend(compressed)

        return self._call_llm(llm_messages)

    def parse_jd(self, jd_text: str) -> dict:
        """解析JD文本为结构化信息"""
        prompt = JD_PARSE_PROMPT.format(jd_text=jd_text)
        messages = [
            {"role": "system", "content": "你是一个专业的岗位描述分析师。"},
            {"role": "user", "content": prompt}
        ]

        result = self._call_llm(messages, temperature=0.3)

        # 尝试提取JSON
        try:
            # 处理可能的markdown代码块包裹
            text = result.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
                if text.startswith("json"):
                    text = text[4:].strip()
            return json.loads(text)
        except json.JSONDecodeError:
            # 如果解析失败，返回原始文本
            return {"raw_text": result, "parse_error": True}

    def _extract_json(self, text: str) -> dict | None:
        """从LLM响应中提取JSON，处理各种格式"""
        text = text.strip()

        # 方法1: 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 方法2: 去除 markdown 代码块
        # 匹配 ```json ... ``` 或 ``` ... ```
        code_block = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
        if code_block:
            try:
                return json.loads(code_block.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 方法3: 找到第一个 { 和最后一个 }，提取中间内容
        first_brace = text.find('{')
        last_brace = text.rfind('}')
        if first_brace != -1 and last_brace > first_brace:
            json_str = text[first_brace:last_brace + 1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # 方法4: 找到第一个 [ 和最后一个 ]
        first_bracket = text.find('[')
        last_bracket = text.rfind(']')
        if first_bracket != -1 and last_bracket > first_bracket:
            json_str = text[first_bracket:last_bracket + 1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        return None

    def generate_profile(self, messages: list[Message]) -> dict:
        """基于对话历史生成完整画像"""
        # 构建对话文本
        conversation_text = "\n\n".join(
            f"{'招聘方' if m.role == 'user' else '分析师'}：{m.content}"
            for m in messages
        )

        prompt = PROFILE_GENERATE_PROMPT.format(conversation_text=conversation_text)
        llm_messages = [
            {"role": "system", "content": "你是一个专业的人才画像生成器。基于对话记录输出结构化JSON。"},
            {"role": "user", "content": prompt}
        ]

        result = self._call_llm(llm_messages, temperature=0.3)
        print(f"[DEBUG] generate_profile LLM返回 (前500字符): {result[:500]}")

        # 使用健壮的 JSON 提取
        profile = self._extract_json(result)
        if profile:
            print(f"[DEBUG] JSON解析成功，job_title: {profile.get('job_title', '无')}")
            return profile

        # 第一次失败，尝试用更明确的提示重试
        print("[DEBUG] 首次JSON解析失败，尝试重试...")
        retry_messages = [
            {"role": "system", "content": "你是一个JSON生成器。只输出纯JSON，不要任何其他文字。"},
            {"role": "user", "content": f"以下是一段对话记录，请基于它生成人才画像的JSON。\n\n{conversation_text}\n\n请直接输出JSON，不要包含任何说明文字或markdown标记。"}
        ]
        result2 = self._call_llm(retry_messages, temperature=0.1)
        print(f"[DEBUG] 重试LLM返回 (前500字符): {result2[:500]}")
        profile = self._extract_json(result2)
        if profile:
            print(f"[DEBUG] 重试JSON解析成功，job_title: {profile.get('job_title', '无')}")
            return profile

        print(f"[DEBUG] 两次JSON解析均失败，返回原始文本")
        return {"raw_text": result, "generate_error": True}
