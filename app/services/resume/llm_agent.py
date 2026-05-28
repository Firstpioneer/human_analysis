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
        3. "project_experiences" (项目经历): 从简历中抽取项目，不要大段复述原文。
           - name: 项目名称，无法判断时用业务/系统名称概括
           - summary: 80字以内的项目经历总结，说明候选人做了什么和产生了什么结果
           - role: 候选人在项目中的角色或责任，无法判断则为空字符串
           - tech_stack: 3-8个从项目内容推断出的技术关键词
           - impact: 可验证成果或业务影响，无法判断则为空字符串
           - evidence: 支撑该总结的简短原文证据，120字以内
        4. "formatted_claims" (规整后的能力声明): 将 claims 归纳为可读分组。
           - category: 类别，如后端开发、前端开发、AI/算法、工程实践、协作管理
           - items: 该类别下的能力关键词或短句
           - evidence: 简短证据或来源说明，无法判断则为空字符串
           - signal_strength: 1-5
        5. "multidimensional_profile" (多维履历画像): 像 MBTI 维度一样，根据简历证据给出候选人的职业倾向坐标。
           - dimensions: 4-8个维度。每个维度包含 key、left_label、right_label、score、summary、evidence、confidence。
             score 为 0-100，越接近 0 越偏 left_label，越接近 100 越偏 right_label；50 表示证据不足或中性。
             必须至少覆盖：软件实现/硬件工程、技术深耕/业务管理、独立产出/协作沟通、数据分析/人际服务。
             可按候选人经历增加：探索创新/流程执行、规划推进/灵活适应、内部平台/客户现场等维度。
           - overall_tags: 3-6个画像标签，如"软件工程型"、"数据驱动"、"跨部门协同"。
           - summary: 120字以内总结画像，不要做心理诊断，只描述履历证据呈现出的工作倾向。
        6. "suitable_roles" (适合投递岗位): 根据项目、能力声明和多维画像推荐3-5个岗位。岗位池可由企业数据库替换，此处先输出通用岗位建议。
           - title: 岗位名称
           - reason: 60字以内推荐理由
           - matching_skills: 3-6个匹配技能
           - fit_score: 0-100契合度，综合技能证据、项目经历、多维画像和信息盲区得出
           - fit_reason: 40字以内说明契合度的主要依据
           - risk: 需要面试确认的风险点，无法判断则为空字符串
        7. "interview_questions" (AI面试辅助问题): 根据项目、岗位建议和盲区拟定6-10个问题。
           - question: 问题内容
           - purpose: 考察目的
           - based_on: 关联的项目/技能/盲区
           - difficulty: "easy", "medium", "hard"
        7. "blind_spots" (信息盲区): 提出1-3个需要面试官在后续重点追问的漏洞（如"写了负责某系统，但未提及具体使用的技术栈或业务指标"）。

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
            "formatted_claims": self._normalize_formatted_claims(
                result.get("formatted_claims") or fallback.get("formatted_claims", [])
            ),
            "objective_experiences": result.get("objective_experiences") or fallback.get("objective_experiences", []),
            "project_experiences": self._normalize_projects(
                result.get("project_experiences") or fallback.get("project_experiences", [])
            ),
            "multidimensional_profile": self._normalize_multidimensional_profile(
                result.get("multidimensional_profile") or fallback.get("multidimensional_profile", {})
            ),
            "suitable_roles": self._normalize_roles(
                result.get("suitable_roles") or fallback.get("suitable_roles", [])
            ),
            "interview_questions": self._normalize_questions(
                result.get("interview_questions") or fallback.get("interview_questions", [])
            ),
            "blind_spots": result.get("blind_spots") or fallback.get("blind_spots", []),
        }

    def _heuristic_response(self, clean_text: str) -> dict:
        contact = self._extract_contact(clean_text)
        lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
        name = self._guess_name(lines)
        claims = self._extract_claims(lines)
        experiences = self._extract_experiences(lines)
        projects = self._build_project_experiences(experiences, lines)
        formatted_claims = self._format_claims(claims)
        multidimensional_profile = self._build_multidimensional_profile(clean_text, projects, formatted_claims, experiences, claims)
        roles = self._suggest_roles(projects, formatted_claims, multidimensional_profile)
        blind_spots = self._build_blind_spots(experiences, claims)
        return {
            "name": name,
            "contact": contact,
            "claims": claims,
            "formatted_claims": formatted_claims,
            "objective_experiences": experiences,
            "project_experiences": projects,
            "multidimensional_profile": multidimensional_profile,
            "suitable_roles": roles,
            "interview_questions": self._build_interview_questions(projects, roles, blind_spots),
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

    def _normalize_projects(self, projects: list[dict]) -> list[dict]:
        normalized = []
        for idx, project in enumerate(projects or [], start=1):
            if not isinstance(project, dict):
                continue
            tech_stack = project.get("tech_stack") or []
            if isinstance(tech_stack, str):
                tech_stack = [item.strip() for item in re.split(r"[,，/、\s]+", tech_stack) if item.strip()]
            normalized.append({
                "name": str(project.get("name") or f"项目 {idx}")[:80],
                "summary": str(project.get("summary") or "")[:180],
                "role": str(project.get("role") or "")[:80],
                "tech_stack": [str(item)[:30] for item in tech_stack[:8]],
                "impact": str(project.get("impact") or "")[:120],
                "evidence": str(project.get("evidence") or "")[:160],
            })
        return normalized[:8]

    def _normalize_formatted_claims(self, formatted_claims: list[dict]) -> list[dict]:
        normalized = []
        for claim in formatted_claims or []:
            if not isinstance(claim, dict):
                continue
            items = claim.get("items") or []
            if isinstance(items, str):
                items = [item.strip() for item in re.split(r"[,，/、；;]", items) if item.strip()]
            normalized.append({
                "category": str(claim.get("category") or "综合能力")[:40],
                "items": [str(item)[:60] for item in items[:8]],
                "evidence": str(claim.get("evidence") or "")[:140],
                "signal_strength": self._clamp_score(claim.get("signal_strength", 3)),
            })
        return normalized[:8]

    def _normalize_roles(self, roles: list[dict]) -> list[dict]:
        normalized = []
        for role in roles or []:
            if not isinstance(role, dict):
                continue
            skills = role.get("matching_skills") or []
            if isinstance(skills, str):
                skills = [item.strip() for item in re.split(r"[,，/、\s]+", skills) if item.strip()]
            normalized.append({
                "title": str(role.get("title") or "")[:60],
                "reason": str(role.get("reason") or "")[:140],
                "matching_skills": [str(item)[:30] for item in skills[:6]],
                "fit_score": self._clamp_percent(role.get("fit_score", 70)),
                "fit_reason": str(role.get("fit_reason") or "")[:80],
                "risk": str(role.get("risk") or "")[:120],
            })
        return [role for role in normalized if role["title"]][:5]

    def _normalize_multidimensional_profile(self, profile: dict) -> dict:
        if not isinstance(profile, dict):
            profile = {}
        dimensions = []
        for dim in profile.get("dimensions", []) or []:
            if not isinstance(dim, dict):
                continue
            left = str(dim.get("left_label") or "")[:20]
            right = str(dim.get("right_label") or "")[:20]
            if not left or not right:
                continue
            dimensions.append({
                "key": str(dim.get("key") or f"{left}_{right}")[:40],
                "left_label": left,
                "right_label": right,
                "score": self._clamp_percent(dim.get("score", 50)),
                "summary": str(dim.get("summary") or "")[:120],
                "evidence": str(dim.get("evidence") or "")[:160],
                "confidence": self._clamp_score(dim.get("confidence", 3)),
            })
        tags = profile.get("overall_tags") or []
        if isinstance(tags, str):
            tags = [item.strip() for item in re.split(r"[,，/、\s]+", tags) if item.strip()]
        normalized = {
            "dimensions": dimensions[:8],
            "overall_tags": [str(tag)[:20] for tag in tags[:6]],
            "summary": str(profile.get("summary") or "")[:160],
        }
        return normalized

    def _normalize_questions(self, questions: list[dict]) -> list[dict]:
        normalized = []
        for question in questions or []:
            if isinstance(question, str):
                question = {"question": question}
            if not isinstance(question, dict):
                continue
            difficulty = question.get("difficulty") or "medium"
            if difficulty not in ("easy", "medium", "hard"):
                difficulty = "medium"
            normalized.append({
                "question": str(question.get("question") or "")[:180],
                "purpose": str(question.get("purpose") or "")[:120],
                "based_on": str(question.get("based_on") or "")[:80],
                "difficulty": difficulty,
            })
        return [q for q in normalized if q["question"]][:10]

    def _clamp_score(self, value) -> int:
        try:
            return max(1, min(5, int(value)))
        except (TypeError, ValueError):
            return 3

    def _clamp_percent(self, value) -> int:
        try:
            return max(0, min(100, int(round(float(value)))))
        except (TypeError, ValueError):
            return 50

    def _build_project_experiences(self, experiences: list[dict], lines: list[str]) -> list[dict]:
        projects = []
        source_experiences = experiences or []
        if not source_experiences:
            source_experiences = [
                {"description": line, "title": self._guess_title(line)}
                for line in lines
                if any(k in line for k in ("项目", "系统", "平台", "开发", "设计", "优化"))
            ][:6]
        for idx, exp in enumerate(source_experiences[:8], start=1):
            desc = exp.get("description", "")
            if not desc:
                continue
            projects.append({
                "name": self._guess_project_name(desc, idx),
                "summary": self._summarize_project(desc),
                "role": exp.get("title", ""),
                "tech_stack": self._extract_tech_stack(desc),
                "impact": self._extract_impact(desc),
                "evidence": desc[:160],
            })
        return self._normalize_projects(projects)

    def _guess_project_name(self, text: str, idx: int) -> str:
        patterns = [
            r"([\u4e00-\u9fa5A-Za-z0-9_.-]{2,30}(?:项目|系统|平台|网站|小程序|应用|服务))",
            r"(?:项目名称|项目)[:：]\s*([\u4e00-\u9fa5A-Za-z0-9_.-]{2,30})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return f"项目 {idx}"

    def _summarize_project(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        clauses = re.split(r"[。；;]\s*", text)
        useful = [c for c in clauses if any(k in c for k in ("负责", "参与", "开发", "设计", "实现", "优化", "上线", "搭建"))]
        summary = "；".join(useful[:2]) if useful else text
        return summary[:120]

    def _extract_tech_stack(self, text: str) -> list[str]:
        known = [
            "Python", "Java", "Go", "Golang", "C++", "JavaScript", "TypeScript", "Vue", "React",
            "Node.js", "FastAPI", "Django", "Flask", "Spring", "Spring Boot", "MySQL", "PostgreSQL",
            "Redis", "MongoDB", "Elasticsearch", "Docker", "Kubernetes", "Linux", "Nginx",
            "Pytorch", "PyTorch", "TensorFlow", "LLM", "RAG", "OCR", "Pandas", "NumPy",
            "C语言", "C++", "STM32", "FPGA", "PCB", "嵌入式", "单片机", "传感器",
        ]
        found = []
        lower = text.lower()
        for tech in known:
            if tech.lower() in lower and tech not in found:
                found.append("Go" if tech == "Golang" else tech)
        chinese_tech = re.findall(r"(?:使用|基于|采用|技术栈[:：]?)([\u4e00-\u9fa5A-Za-z0-9+_.#/\-、，,\s]{2,80})", text)
        for chunk in chinese_tech:
            chunk = re.split(r"[。；;，,]\s*(?:负责|参与|开发|设计|实现|优化|上线|提升|降低)", chunk)[0]
            for item in re.split(r"[,，/、\s]+", chunk):
                item = item.strip()
                if (
                    1 < len(item) <= 24
                    and item not in found
                    and not any(k in item for k in ("负责", "参与", "开发", "设计", "实现", "优化", "上线", "提升", "降低"))
                ):
                    found.append(item)
                if len(found) >= 8:
                    return found
        return found[:8]

    def _extract_impact(self, text: str) -> str:
        match = re.search(r"([^。；;]*(?:提升|降低|节省|增长|稳定|上线|落地|支持|减少|优化)[^。；;]*\d*[^。；;]*)", text)
        return match.group(1).strip()[:120] if match else ""

    def _format_claims(self, claims: list[dict]) -> list[dict]:
        buckets: dict[str, dict] = {}
        for claim in claims[:16]:
            content = claim.get("content", "")
            category = self._claim_category(content)
            bucket = buckets.setdefault(category, {
                "category": category,
                "items": [],
                "evidence": "",
                "signal_strength": 1,
            })
            item = re.sub(r"^[•\-*\d.、\s]+", "", content).strip()
            if item and item not in bucket["items"]:
                bucket["items"].append(item[:60])
            if not bucket["evidence"]:
                bucket["evidence"] = content[:120]
            bucket["signal_strength"] = max(bucket["signal_strength"], self._clamp_score(claim.get("signal_strength", 3)))
        return self._normalize_formatted_claims(list(buckets.values()))

    def _claim_category(self, content: str) -> str:
        if any(k in content for k in ("前端", "Vue", "React", "JavaScript", "TypeScript", "HTML", "CSS")):
            return "前端开发"
        if any(k in content for k in ("后端", "Python", "Java", "Go", "Spring", "FastAPI", "Django", "Flask")):
            return "后端开发"
        if any(k in content for k in ("算法", "模型", "机器学习", "深度学习", "LLM", "RAG", "NLP", "OCR")):
            return "AI/算法"
        if any(k in content for k in ("Docker", "Kubernetes", "Linux", "部署", "运维", "CI", "CD")):
            return "工程实践"
        if any(k in content for k in ("沟通", "团队", "协作", "管理", "推进")):
            return "协作管理"
        return "综合能力"

    def _build_multidimensional_profile(
        self,
        clean_text: str,
        projects: list[dict],
        formatted_claims: list[dict],
        experiences: list[dict],
        claims: list[dict],
    ) -> dict:
        text = clean_text.lower()
        techs = {tech for project in projects for tech in project.get("tech_stack", [])}
        categories = {claim.get("category") for claim in formatted_claims}
        evidence = self._pick_evidence(projects, experiences, claims)

        def score(left_words, right_words, default=50):
            left_hits = sum(1 for word in left_words if word.lower() in text)
            right_hits = sum(1 for word in right_words if word.lower() in text)
            if left_hits == right_hits == 0:
                return default
            raw = 50 + (right_hits - left_hits) * 14
            return self._clamp_percent(raw)

        sw_hw = score(
            ["python", "java", "go", "javascript", "typescript", "vue", "react", "后端", "前端", "软件", "系统", "平台", "算法", "api"],
            ["硬件", "嵌入式", "单片机", "pcb", "fpga", "电路", "芯片", "传感器", "机械", "自动化"],
            35 if techs or categories & {"后端开发", "前端开发", "AI/算法"} else 50,
        )
        tech_biz = score(
            ["架构", "算法", "开发", "性能", "数据库", "模型", "技术栈", "代码", "接口"],
            ["产品", "运营", "业务", "销售", "市场", "管理", "预算", "增长", "商业"],
        )
        solo_collab = score(
            ["独立", "个人", "负责模块", "开发实现", "编码"],
            ["协作", "团队", "跨部门", "沟通", "推进", "管理", "组织", "协调", "客户"],
        )
        data_people = score(
            ["数据", "分析", "指标", "报表", "建模", "统计", "实验", "a/b", "量化"],
            ["人事", "hr", "招聘", "培训", "员工", "客户", "用户访谈", "沟通", "关系"],
        )
        innovation_process = score(
            ["创新", "探索", "研究", "从0到1", "原型", "论文", "专利"],
            ["流程", "规范", "交付", "执行", "维护", "测试", "运营", "标准化"],
        )
        planning_flex = score(
            ["计划", "排期", "项目管理", "里程碑", "规划", "落地"],
            ["快速响应", "灵活", "迭代", "敏捷", "适应", "临时", "应急"],
        )

        dimensions = [
            self._dimension("software_hardware", "软件实现", "硬件工程", sw_hw, evidence),
            self._dimension("technical_business", "技术深耕", "业务管理", tech_biz, evidence),
            self._dimension("solo_collaboration", "独立产出", "协作沟通", solo_collab, evidence),
            self._dimension("data_people", "数据分析", "人际服务", data_people, evidence),
            self._dimension("innovation_process", "探索创新", "流程执行", innovation_process, evidence),
            self._dimension("planning_flexible", "规划推进", "灵活适应", planning_flex, evidence),
        ]
        tags = []
        if sw_hw < 40:
            tags.append("软件工程型")
        elif sw_hw > 60:
            tags.append("硬件工程型")
        if tech_biz < 45:
            tags.append("技术深耕")
        elif tech_biz > 60:
            tags.append("业务管理")
        if solo_collab > 58 or data_people > 58:
            tags.append("沟通协同")
        if data_people < 42:
            tags.append("数据驱动")
        if innovation_process < 42:
            tags.append("探索创新")
        if not tags:
            tags = ["综合发展型"]
        summary = "；".join(tags[:3]) + "，建议结合岗位要求继续验证关键项目中的个人贡献和产出指标。"
        return self._normalize_multidimensional_profile({
            "dimensions": dimensions,
            "overall_tags": tags,
            "summary": summary,
        })

    def _dimension(self, key: str, left: str, right: str, score: int, evidence: str) -> dict:
        leaning = left if score < 45 else (right if score > 55 else "均衡")
        return {
            "key": key,
            "left_label": left,
            "right_label": right,
            "score": score,
            "summary": f"当前证据偏向{leaning}。",
            "evidence": evidence,
            "confidence": 4 if evidence else 2,
        }

    def _pick_evidence(self, projects: list[dict], experiences: list[dict], claims: list[dict]) -> str:
        for project in projects:
            if project.get("summary"):
                return project["summary"][:160]
            if project.get("evidence"):
                return project["evidence"][:160]
        for exp in experiences:
            if exp.get("description"):
                return exp["description"][:160]
        for claim in claims:
            if claim.get("content"):
                return claim["content"][:160]
        return ""

    def _profile_score(self, profile: dict, key: str, default: int = 50) -> int:
        for dim in (profile or {}).get("dimensions", []):
            if dim.get("key") == key:
                return self._clamp_percent(dim.get("score", default))
        return default

    def _suggest_roles(self, projects: list[dict], formatted_claims: list[dict], multidimensional_profile: dict | None = None) -> list[dict]:
        techs = {tech for project in projects for tech in project.get("tech_stack", [])}
        categories = {claim.get("category") for claim in formatted_claims}
        profile = multidimensional_profile or {}
        software_hardware = self._profile_score(profile, "software_hardware", 50)
        technical_business = self._profile_score(profile, "technical_business", 50)
        solo_collab = self._profile_score(profile, "solo_collaboration", 50)
        data_people = self._profile_score(profile, "data_people", 50)
        roles = []
        if categories & {"后端开发"} or techs & {"Python", "Java", "Go", "FastAPI", "Spring Boot", "MySQL", "Redis"}:
            fit = self._clamp_percent(82 - max(0, software_hardware - 40) + max(0, 50 - technical_business) // 3)
            roles.append({
                "title": "后端开发工程师",
                "reason": "项目和技能中出现服务端开发、数据库或接口实现相关信号。",
                "matching_skills": list((techs & {"Python", "Java", "Go", "FastAPI", "Spring Boot", "MySQL", "Redis"}) or ["服务端开发"]),
                "fit_score": fit,
                "fit_reason": "软件实现和技术深耕信号较强。",
                "risk": "需要确认系统设计深度、性能指标和个人贡献边界。",
            })
        if categories & {"前端开发"} or techs & {"Vue", "React", "JavaScript", "TypeScript"}:
            fit = self._clamp_percent(78 - max(0, software_hardware - 45) + max(0, solo_collab - 55) // 4)
            roles.append({
                "title": "前端开发工程师",
                "reason": "简历体现前端框架、页面开发或交互实现经验。",
                "matching_skills": list((techs & {"Vue", "React", "JavaScript", "TypeScript"}) or ["前端工程化"]),
                "fit_score": fit,
                "fit_reason": "前端技能和协作交付信号匹配。",
                "risk": "需要确认组件设计、状态管理和工程化实践。",
            })
        if categories & {"AI/算法"} or techs & {"PyTorch", "TensorFlow", "LLM", "RAG", "OCR"}:
            fit = self._clamp_percent(80 - max(0, software_hardware - 45) + max(0, 45 - data_people) // 4)
            roles.append({
                "title": "AI应用开发工程师",
                "reason": "存在模型、LLM、OCR或AI应用落地相关信号。",
                "matching_skills": list((techs & {"PyTorch", "TensorFlow", "LLM", "RAG", "OCR", "Python"}) or ["AI应用"]),
                "fit_score": fit,
                "fit_reason": "AI技术栈和数据分析倾向支撑岗位匹配。",
                "risk": "需要确认模型调用、数据处理和效果评估是否为本人完成。",
            })
        if software_hardware > 60 or techs & {"C语言", "C++", "STM32", "FPGA", "PCB", "嵌入式", "单片机", "传感器"}:
            hardware_skills = techs & {"C语言", "C++", "STM32", "FPGA", "PCB", "嵌入式", "单片机", "传感器"}
            roles.append({
                "title": "嵌入式/硬件工程师",
                "reason": "简历中出现硬件、嵌入式、电路或设备调试相关信号。",
                "matching_skills": list(hardware_skills)[:6] or ["硬件工程", "嵌入式开发"],
                "fit_score": self._clamp_percent(70 + max(0, software_hardware - 60) // 2),
                "fit_reason": "软件-硬件画像明显偏硬件工程侧。",
                "risk": "需要确认硬件设计、调试记录和量产/交付经验。",
            })
        if data_people > 60 or categories & {"协作管理"}:
            roles.append({
                "title": "HR/人才发展专员",
                "reason": "简历呈现人际沟通、组织协调或人事相关信号。",
                "matching_skills": ["沟通协调", "人员支持", "流程推进"],
                "fit_score": self._clamp_percent(68 + max(0, data_people - 60) // 2 + max(0, solo_collab - 55) // 3),
                "fit_reason": "人际服务和协作沟通信号较明显。",
                "risk": "需要确认人事制度、招聘流程或员工关系经验深度。",
            })
        if not roles:
            roles.append({
                "title": "软件开发工程师",
                "reason": "简历中存在项目开发经历，但岗位方向需要通过面试进一步聚焦。",
                "matching_skills": list(techs)[:6] or ["项目开发"],
                "fit_score": self._clamp_percent(62 + max(0, 50 - software_hardware) // 3),
                "fit_reason": "项目开发证据存在，但方向聚焦度一般。",
                "risk": "简历技术栈和项目结果不够清晰。",
            })
        return self._normalize_roles(roles)

    def _build_interview_questions(self, projects: list[dict], roles: list[dict], blind_spots: list[str]) -> list[dict]:
        questions = []
        for project in projects[:4]:
            name = project.get("name") or "该项目"
            questions.append({
                "question": f"请用3分钟说明{name}的业务目标、你的职责、核心技术方案和最终结果。",
                "purpose": "验证项目真实性、职责边界和表达结构。",
                "based_on": name,
                "difficulty": "medium",
            })
            if project.get("tech_stack"):
                questions.append({
                    "question": f"{name}中为什么选择{project['tech_stack'][0]}，当时还比较过哪些替代方案？",
                    "purpose": "考察技术选型能力和实际参与深度。",
                    "based_on": project["tech_stack"][0],
                    "difficulty": "medium",
                })
        for role in roles[:2]:
            questions.append({
                "question": f"如果投递{role.get('title')}，你认为自己最匹配的两个项目证据是什么？",
                "purpose": "考察岗位匹配度和自我认知。",
                "based_on": role.get("title", ""),
                "difficulty": "easy",
            })
        for spot in blind_spots[:2]:
            questions.append({
                "question": f"简历中有一个需要确认的点：{spot} 请补充具体背景、技术细节和可量化结果。",
                "purpose": "补齐简历盲区。",
                "based_on": "信息盲区",
                "difficulty": "hard",
            })
        return self._normalize_questions(questions)
