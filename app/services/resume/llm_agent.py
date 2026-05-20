"""简历语义分析 Agent（阿里云 DashScope / Qwen）"""
import json
import os
import re
import logging
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class SemanticAnalyzerAgent:
    def __init__(self):
        self._api_key = os.getenv("DASHSCOPE_API_KEY")
        if not self._api_key:
            logging.warning("未检测到 DASHSCOPE_API_KEY 环境变量，简历语义分析功能将不可用。")
        self._client = None
        self._base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    @property
    def client(self):
        if self._client is None:
            if not self._api_key:
                raise RuntimeError("未配置 DASHSCOPE_API_KEY，无法调用语义分析服务")
            self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._client
        self.system_prompt = """
        你是一个严谨的 HR 数据分析专家。你的任务是解析候选人的简历文本，并进行"经历与声明"的分离。
        请严格以 JSON 格式输出，包含以下三个数组：

        1. "claims" (能力声明): 候选人主观标榜的能力（如"精通Python", "有较强的团队合作能力"）。
           - signal_strength (1-5): 根据具体程度打分。纯空话为1，带有一定背景说明的为3及以上。
        2. "objective_experiences" (客观经历): 包含具体公司、时间、STAR原则（情境、任务、行动、结果）的具体事实。
           - signal_strength (1-5): 数据指标越具体、事实越清晰，得分越高。
           - star_completeness: "high", "medium", "low"。
        3. "blind_spots" (信息盲区): 提出1-2个需要面试官在后续重点追问的漏洞（如"写了负责某系统，但未提及具体使用的技术栈或业务指标"）。

        必须且只能输出纯 JSON 格式数据，不要带有 ```json 等 Markdown 标记，不要输出多余的解释。
        """

    def _extract_json(self, text: str) -> str:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return match.group(0)
        return text

    def analyze(self, clean_text: str) -> dict:
        logging.info("启动深度思考模型 (Qwen) 进行语义剖析...")
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"请解析以下简历文本：\n{clean_text}"}
        ]
        try:
            completion = self.client.chat.completions.create(
                model="qwen-max",
                messages=messages,
                extra_body={"enable_thinking": True},
                stream=True
            )
            is_answering = False
            final_content = ""
            print(f"\n\033[96m{'=' * 20} 🧠 大模型深度思考过程 {'=' * 20}\033[0m")
            for chunk in completion:
                delta = chunk.choices[0].delta
                if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                    if not is_answering:
                        print(f"\033[90m{delta.reasoning_content}\033[0m", end="", flush=True)
                if hasattr(delta, "content") and delta.content:
                    if not is_answering:
                        print(f"\n\033[92m{'=' * 20} 🚀 思考结束，生成结构化档案 {'=' * 20}\033[0m\n")
                        is_answering = True
                    final_content += delta.content
            json_str = self._extract_json(final_content)
            result = json.loads(json_str)
            logging.info("语义分析与结构化提取完成。")
            return result
        except json.JSONDecodeError as e:
            logging.error(f"大模型返回的数据无法被解析为 JSON: {e}\n原始文本: {final_content}")
            return self._fallback_response()
        except Exception as e:
            logging.error(f"API 调用失败: {e}")
            return self._fallback_response()

    def _fallback_response(self) -> dict:
        return {
            "claims": [],
            "objective_experiences": [],
            "blind_spots": ["【系统提示】AI 语义分析失败，请人工复核原始简历原件。"]
        }
