"""画像 Agent — DeepSeek LLM 对话与画像生成"""
from typing import Optional

from openai import OpenAI
from app.models.portrait import Message
from app.services.portrait.prompts import AGENT_SYSTEM_PROMPT, JD_PARSE_PROMPT, PROFILE_GENERATE_PROMPT
import config
import json
import re


class RecruitmentAgent:
    def __init__(self, api_key: str):
        self.client = OpenAI(
            api_key=api_key,
            base_url=config.PORTRAIT_LLM_BASE_URL
        )
        self.model = config.PORTRAIT_LLM_MODEL

    def _call_llm(self, messages: list[dict], temperature: float = 0.7) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=4096
        )
        return response.choices[0].message.content

    def _build_context_summary(self, profile_draft: Optional[dict]) -> str:
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
        if len(messages) <= max_recent:
            return [{"role": m.role, "content": m.content} for m in messages]
        old_messages = messages[:-max_recent]
        recent_messages = messages[-max_recent:]
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

    def chat(self, messages: list[Message], profile_draft: Optional[dict] = None) -> str:
        system_content = AGENT_SYSTEM_PROMPT
        context_summary = self._build_context_summary(profile_draft)
        if context_summary:
            system_content += f"\n\n{context_summary}"
        llm_messages = [{"role": "system", "content": system_content}]
        compressed = self._compress_old_messages(messages)
        llm_messages.extend(compressed)
        return self._call_llm(llm_messages)

    def parse_jd(self, jd_text: str) -> dict:
        prompt = JD_PARSE_PROMPT.format(jd_text=jd_text)
        messages = [
            {"role": "system", "content": "你是一个专业的岗位描述分析师。"},
            {"role": "user", "content": prompt}
        ]
        result = self._call_llm(messages, temperature=0.3)
        try:
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
            return {"raw_text": result, "parse_error": True}

    def _extract_json(self, text: str) -> Optional[dict]:
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        code_block = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
        if code_block:
            try:
                return json.loads(code_block.group(1).strip())
            except json.JSONDecodeError:
                pass
        first_brace = text.find('{')
        last_brace = text.rfind('}')
        if first_brace != -1 and last_brace > first_brace:
            json_str = text[first_brace:last_brace + 1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
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
        profile = self._extract_json(result)
        if profile:
            return profile
        retry_messages = [
            {"role": "system", "content": "你是一个JSON生成器。只输出纯JSON，不要任何其他文字。"},
            {"role": "user", "content": f"以下是一段对话记录，请基于它生成人才画像的JSON。\n\n{conversation_text}\n\n请直接输出JSON，不要包含任何说明文字或markdown标记。"}
        ]
        result2 = self._call_llm(retry_messages, temperature=0.1)
        profile = self._extract_json(result2)
        if profile:
            return profile
        return {"raw_text": result, "generate_error": True}
