"""简历语义分析 Agent（阿里云 DashScope / Qwen）"""
import json
import re
import logging
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class SemanticAnalyzerAgent:
    def __init__(self):
        self._api_key = config.RESUME_LLM_API_KEY
        if not self._api_key:
            logging.warning("未检测到 RESUME_LLM_API_KEY/DASHSCOPE_API_KEY，简历语义分析将使用本地规则回退。")
        self._client = None
        self._base_url = config.RESUME_LLM_BASE_URL
        self._model = config.RESUME_LLM_MODEL
        self.system_prompt = """
        你是一个严谨的 HR 数据分析专家。你的任务是解析候选人的简历文本，并进行"经历与声明"的分离。
        请严格以 JSON 格式输出，包含以下字段：

        - name: 候选人姓名，无法判断则为空字符串
        - contact: 对象，包含 email、phone、github、blog

        1. "claims" (能力声明): 候选人主观标榜的能力（如"精通Python", "有较强的团队合作能力"）。
           - content: 声明内容
           - signal_strength (1-5): 根据具体程度打分。纯空话为1，带有一定背景说明的为3及以上。
        2. "objective_experiences" (客观经历): 包含具体公司、时间、STAR原则（情境、任务、行动、结果）的具体事实。
           - company, title, start_date, end_date, description
           - signal_strength (1-5): 数据指标越具体、事实越清晰，得分越高。
           - star_completeness: "high", "medium", "low"。
        3. "blind_spots" (信息盲区): 提出1-2个需要面试官在后续重点追问的漏洞（如"写了负责某系统，但未提及具体使用的技术栈或业务指标"）。

        必须且只能输出纯 JSON 格式数据，不要带有 ```json 等 Markdown 标记，不要输出多余的解释。
        """

    @property
    def client(self):
        if self._client is None:
            if not self._api_key:
                raise RuntimeError("未配置 RESUME_LLM_API_KEY，无法调用语义分析服务")
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._client

    def _extract_json(self, text: str) -> str:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return match.group(0)
        return text

    def analyze(self, clean_text: str) -> dict:
        if not self._api_key:
            return self._heuristic_response(clean_text)

        logging.info("启动深度思考模型 (Qwen) 进行语义剖析...")
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"请解析以下简历文本：\n{clean_text}"}
        ]
        try:
            completion = self.client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.2,
                max_tokens=3000,
            )
            final_content = completion.choices[0].message.content or ""
            json_str = self._extract_json(final_content)
            result = json.loads(json_str)
            logging.info("语义分析与结构化提取完成。")
            return self._normalize_result(result, clean_text)
        except json.JSONDecodeError as e:
            logging.error(f"大模型返回的数据无法被解析为 JSON: {e}\n原始文本: {final_content}")
            return self._heuristic_response(clean_text)
        except Exception as e:
            logging.error(f"API 调用失败: {e}")
            return self._heuristic_response(clean_text)

    def _normalize_result(self, result: dict, clean_text: str) -> dict:
        fallback = self._heuristic_response(clean_text)
        contact = fallback.get("contact", {})
        contact.update(result.get("contact") or {})
        return {
            "name": result.get("name") or fallback.get("name", ""),
            "contact": contact,
            "claims": result.get("claims") or fallback.get("claims", []),
            "objective_experiences": result.get("objective_experiences") or fallback.get("objective_experiences", []),
            "blind_spots": result.get("blind_spots") or fallback.get("blind_spots", []),
        }

    def _heuristic_response(self, clean_text: str) -> dict:
        contact = self._extract_contact(clean_text)
        lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
        name = self._guess_name(lines)
        claims = self._extract_claims(lines)
        experiences = self._extract_experiences(lines)
        blind_spots = self._build_blind_spots(experiences, claims)
        return {
            "name": name,
            "contact": contact,
            "claims": claims,
            "objective_experiences": experiences,
            "blind_spots": blind_spots,
        }

    def _extract_contact(self, text: str) -> dict:
        contact = {}
        email = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
        phone = re.search(r"(?<!\d)(?:\+?86[-\s]?)?1[3-9]\d{9}(?!\d)", text)
        github = re.search(r"https?://(?:www\.)?github\.com/[A-Za-z0-9_.-]+/?", text)
        links = re.findall(r"https?://[^\s，,；;）)]+", text)
        if email:
            contact["email"] = email.group(0)
        if phone:
            contact["phone"] = phone.group(0)
        if github:
            contact["github"] = github.group(0).rstrip("/")
        for link in links:
            if "github.com" not in link and not contact.get("blog"):
                contact["blog"] = link.rstrip("/")
        return contact

    def _guess_name(self, lines: list[str]) -> str:
        blacklist = ("简历", "求职", "个人", "电话", "邮箱", "教育", "工作", "项目")
        for line in lines[:8]:
            compact = re.sub(r"\s+", "", line)
            if 2 <= len(compact) <= 8 and not any(word in compact for word in blacklist):
                if re.fullmatch(r"[\u4e00-\u9fa5A-Za-z·.]+", compact):
                    return compact
        return ""

    def _extract_claims(self, lines: list[str]) -> list[dict]:
        keywords = ("熟悉", "精通", "掌握", "了解", "擅长", "具备", "能力", "经验")
        claims = []
        for line in lines:
            if any(k in line for k in keywords) and len(line) <= 140:
                strength = 4 if re.search(r"\d+|年|项目|上线|优化|提升|降低", line) else 2
                claims.append({"content": line, "signal_strength": strength})
            if len(claims) >= 12:
                break
        return claims

    def _extract_experiences(self, lines: list[str]) -> list[dict]:
        experiences = []
        company_pattern = re.compile(r"([\u4e00-\u9fa5A-Za-z0-9（）()·.\-]{2,30}(?:公司|科技|集团|银行|大学|学院|实验室|工作室))")
        current = None
        for line in lines:
            company_match = company_pattern.search(line)
            has_project_signal = any(k in line for k in ("项目", "系统", "平台", "负责", "参与", "开发", "设计", "优化", "上线"))
            if company_match or has_project_signal:
                if company_match or current is None:
                    current = {
                        "company": company_match.group(1) if company_match else "",
                        "title": self._guess_title(line),
                        "start_date": self._guess_date(line, first=True),
                        "end_date": self._guess_date(line, first=False),
                        "description": line,
                    }
                    experiences.append(current)
                else:
                    current["description"] = (current["description"] + " " + line).strip()
        normalized = []
        for exp in experiences[:10]:
            desc = exp.get("description", "")
            strength = self._score_signal(desc)
            exp["signal_strength"] = strength
            exp["star_completeness"] = "high" if strength >= 4 else ("medium" if strength == 3 else "low")
            normalized.append(exp)
        return normalized

    def _guess_title(self, text: str) -> str:
        titles = ("工程师", "开发", "架构师", "负责人", "经理", "实习", "算法", "测试", "产品", "运维", "前端", "后端")
        for title in titles:
            if title in text:
                return title
        return ""

    def _guess_date(self, text: str, first: bool) -> str:
        dates = re.findall(r"(?:20|19)\d{2}[./年-]?(?:0?[1-9]|1[0-2])?", text)
        if not dates:
            return ""
        return dates[0 if first else -1]

    def _score_signal(self, text: str) -> int:
        score = 1
        if re.search(r"\d+%|\d+\s*(万|千|ms|秒|人|次|QPS|TPS)", text, re.I):
            score += 2
        if any(k in text for k in ("负责", "设计", "实现", "优化", "上线", "落地")):
            score += 1
        if any(k in text for k in ("结果", "提升", "降低", "节省", "增长", "稳定")):
            score += 1
        return min(score, 5)

    def _build_blind_spots(self, experiences: list[dict], claims: list[dict]) -> list[str]:
        blind_spots = []
        if not experiences:
            blind_spots.append("未识别到足够具体的项目或工作经历，需要面试确认真实职责与产出。")
        for exp in experiences[:3]:
            desc = exp.get("description", "")
            if exp.get("signal_strength", 1) <= 2:
                blind_spots.append(f"{exp.get('company') or '某段经历'}描述偏概括，缺少可验证指标、技术栈或个人贡献边界。")
        if claims and not experiences:
            blind_spots.append("简历中技能声明较多，但缺少对应项目证据支撑。")
        return blind_spots[:4]
