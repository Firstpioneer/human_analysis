"""
AI 面试引擎 - 自动交互示例
通过 HTTP API 模拟完整的 AI 面试流程
无需浏览器，自动创建画像 → 简历 → 面试 → 问答 → 结束 → 评估
"""

import json
import time
import urllib.request
import urllib.error

API_BASE = "http://127.0.0.1:5000"

# ==================== 工具函数 ====================


def api(method, path, data=None):
    """调用 API 并返回 (状态码, 响应数据)"""
    url = API_BASE + path
    body = json.dumps(data, ensure_ascii=False).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json; charset=utf-8")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))
    except urllib.error.URLError:
        print("  ❌ 无法连接到服务器，请确保已启动: python app.py")
        return 0, {}


def color(text, code):
    """终端颜色"""
    return f"\033[{code}m{text}\033[0m"


def print_step(icon, title, detail=""):
    """格式化打印步骤"""
    print(f"\n  {icon}  {color(title, '1;36')}")
    if detail:
        for line in detail.split("\n"):
            print(f"     {line}")


def print_bubble(speaker, text, color_code):
    """打印对话气泡"""
    prefix = "🤖 AI 面试官" if speaker == "AI" else "👤 候选人"
    print()
    print(f"  {color(prefix, color_code)}")
    print(f"  {color('─' * 50, '2')}")
    for line in text.split("\n"):
        print(f"    {line}")
    print(f"  {color('─' * 50, '2')}")


# ==================== 模拟回答生成 ====================

# 不同类别的回答模板 — AI 会根据问题内容组合出上下文相关的回答
_ANSWER_PARTS = {
    "技术": {
        "intro": [
            "这个问题我在实际项目中有深入实践。",
            "关于这个技术点，我有比较丰富的经验。",
            "这是我日常工作中经常涉及的技术。",
        ],
        "practice": [
            "在最近的一个项目中，我们使用该技术构建了核心模块，"
            "通过合理的架构设计和技术选型，最终取得了很好的效果。",
            "我主导了相关技术方案的落地，从技术调研、原型验证到"
            "生产部署全程跟进，积累了大量实战经验。",
            "在多个项目中我都应用了这项技术，并总结出了一套最佳实践。",
        ],
        "detail": [
            "具体实现上，我们考虑了性能、可维护性和扩展性，"
            "采用了分层架构设计，各模块职责清晰。",
            "在技术选型时，我们对比了多种方案，最终选择了最适合"
            "业务场景的方案，并在实施过程中持续优化。",
        ],
        "outcome": [
            "最终系统上线后表现稳定，QPS 提升了约 60%，"
            "响应时间降低了 40%，得到了业务方的认可。",
            "该方案使开发效率提升了 30%，同时降低了维护成本。",
        ],
    },
    "项目经验": {
        "intro": [
            "这个项目是我职业生涯中非常有代表性的一个。",
            "我参与的这个项目规模较大，涉及多个团队协作。",
        ],
        "practice": [
            "我在项目中担任技术负责人，负责架构设计和核心模块开发。"
            "项目初期我们面临需求不明确、时间紧张等挑战，"
            "通过敏捷迭代的方式逐步推进。",
            "作为核心开发人员，我主导了关键技术难点的攻关，"
            "包括性能优化、系统解耦和技术栈升级等工作。",
        ],
        "detail": [
            "最具挑战的是系统在高并发场景下的稳定性问题。"
            "我们通过引入缓存、异步处理和读写分离等策略，"
            "最终将系统的可用性提升到了 99.99%。",
            "在项目管理上，我们采用了每日站会和双周迭代的节奏，"
            "确保项目按时交付。",
        ],
        "outcome": [
            "项目成功上线并稳定运行，获得了公司年度优秀项目奖。",
            "该项目为业务带来了显著的增长，用户量增长了 3 倍。",
        ],
    },
    "软技能": {
        "intro": [
            "团队协作是我非常看重的能力。",
            "我认为沟通是解决问题的关键。",
        ],
        "practice": [
            "在一次跨部门合作中，我主动承担了协调工作，"
            "定期组织同步会议，确保各方信息对齐。",
            "当团队出现意见分歧时，我会先倾听各方观点，"
            "然后基于数据和事实进行讨论，推动达成共识。",
        ],
        "detail": [
            "我始终秉持开放和尊重的态度，鼓励团队成员表达想法。"
            "在项目管理中，我注重建立透明的沟通机制。",
            "通过组织技术分享会，帮助团队提升整体技术能力。",
        ],
        "outcome": [
            "团队的协作效率明显提升，项目交付周期缩短了 20%。",
            "团队成员的技术能力和满意度都有显著提高。",
        ],
    },
    "文化契合": {
        "intro": [
            "我非常注重团队文化和价值观的匹配。",
            "我相信一个好的团队文化能激发每个人的潜力。",
        ],
        "practice": [
            "我倾向于透明、开放的工作方式，喜欢主动沟通和分享。"
            "在快速变化的环境中，我能迅速适应并找到自己的节奏。",
            "我认同结果导向的价值观，同时也注重过程中的学习和成长。",
        ],
        "detail": [
            "面对不确定性，我会主动探索和尝试，而不是被动等待。"
            "我习惯在工作中保持记录和总结，不断优化工作方法。",
        ],
        "outcome": [
            "这种工作方式帮助我快速融入了新团队。",
            "持续学习和改进的态度让我在职业发展中不断进步。",
        ],
    },
    "行为": {
        "intro": [
            "这个问题让我回想起一次很有意义的经历。",
            "我有一个很好的例子可以分享。",
        ],
        "practice": [
            "当时情况比较紧急，我迅速分析了问题的关键点，"
            "制定了应对方案并与团队沟通执行。",
            "我主动承担了额外的责任，在完成自己工作的同时"
            "协助同事解决了瓶颈问题。",
        ],
        "detail": [
            "在整个过程中，我特别注意沟通和反馈，"
            "确保所有人都了解进展和变化。",
            "事后我组织了复盘会议，总结经验和改进点。",
        ],
        "outcome": [
            "问题得到了及时解决，并且我们建立了一套预防机制。",
            "这件事之后，团队的处理效率明显提升。",
        ],
    },
}


def generate_mock_answer(question_text: str, category: str = "技术") -> str:
    """根据问题内容和类别生成上下文相关的模拟回答"""
    import random

    # 提取问题中的关键词来引导回答方向
    keywords = []
    for kw in ["Python", "Flask", "React", "Docker", "Redis", "MySQL", "Django",
               "JavaScript", "TypeScript", "Vue", "Node", "API", "架构", "设计",
               "优化", "性能", "安全", "测试", "部署", "监控"]:
        if kw in question_text:
            keywords.append(kw)

    # 选择对应的回答模板类别
    parts = _ANSWER_PARTS.get(category, _ANSWER_PARTS["技术"])

    intro = random.choice(parts["intro"])
    practice = random.choice(parts["practice"])
    detail = random.choice(parts["detail"])
    outcome = random.choice(parts["outcome"])

    # 如果问题中包含具体技术名，加入回答
    tech_detail = ""
    if keywords:
        tech_detail = f"在{', '.join(keywords[:3])}方面，"

    answer = f"{intro}{tech_detail}{practice}{detail}{outcome}"
    return answer


# ==================== 主流程 ====================


def wait_for_server(max_retries=5):
    """等待服务器就绪"""
    for i in range(max_retries):
        status, data = api("GET", "/api/interviews")
        if status == 200:
            return True
        print(f"  ⏳ 等待服务器启动... ({i+1}/{max_retries})")
        time.sleep(1)
    return False


def main():
    print()
    print(color("╔══════════════════════════════════════════════════════╗", "1;35"))
    print(color("║        AI 面试引擎 — 自动交互示例                   ║", "1;35"))
    print(color("╚══════════════════════════════════════════════════════╝", "1;35"))
    print()
    print(color("  本示例将自动模拟一场完整的 AI 面试：", "2"))
    print(color("  ① 创建人才画像  →  ② 上传候选人简历  →  ", "2"))
    print(color("  ③ 启动面试  →  ④ AI 自动问答  →  ⑤ 生成评估", "2"))
    print()

    # ==================== 检查服务器 ====================
    print_step("🔌", "步骤 0: 检查服务器连接")
    if not wait_for_server():
        print(color("  ❌ 服务器连接失败！请先启动: d:/实习/.venv/Scripts/python.exe app.py", "1;31"))
        return
    print(color("  ✅ 服务器已就绪", "1;32"))

    # ==================== 步骤 1: 创建人才画像 ====================
    print_step("📋", "步骤 1: 创建人才画像", "岗位: 高级后端开发工程师 · 技能: Python/Flask/MySQL/Redis/Docker")

    profile = {
        "position": {
            "title": "高级后端开发工程师",
            "department": "技术部",
            "level": "高级",
            "salary_range": "25K-40K",
        },
        "requirements": {
            "education": {"min_degree": "本科", "preferred_majors": ["计算机科学", "软件工程"]},
            "experience": {"min_years": 3, "preferred_industries": ["互联网", "科技"]},
            "skills": [
                {"name": "Python", "level": "精通", "weight": 10},
                {"name": "Flask", "level": "精通", "weight": 9},
                {"name": "MySQL", "level": "熟悉", "weight": 8},
                {"name": "Redis", "level": "熟悉", "weight": 7},
                {"name": "Docker", "level": "熟悉", "weight": 7},
                {"name": "Kubernetes", "level": "了解", "weight": 5},
            ],
            "soft_skills": ["团队协作", "沟通表达", "问题解决"],
        },
        "qualifications": {
            "certifications": [],
            "projects": ["高并发系统设计", "微服务架构迁移"],
            "other": ["有开源项目贡献经历优先"],
        },
        "culture_fit": {
            "team_size": "5-10人",
            "work_style": "敏捷开发",
            "values": ["技术驱动", "结果导向"],
        },
    }

    status, data = api("POST", "/api/profiles", profile)
    if status != 200:
        print(color(f"  ❌ 创建画像失败: {data.get('error', '未知错误')}", "1;31"))
        return
    profile_id = data["profile"]["_id"]
    print(color(f"  ✅ 画像已创建  ID: {profile_id}", "1;32"))

    # ==================== 步骤 2: 上传候选人简历 ====================
    print_step("👤", "步骤 2: 创建候选人档案", "姓名: 王小明 · 5年后端开发经验")

    candidate = {
        "name": "王小明",
        "summary": "5年后端开发经验，擅长 Python/Go，有高并发系统设计和微服务架构经验",
        "contact": {"email": "wangxm@example.com", "phone": "138-0000-0000"},
        "experiences": [
            {
                "company": "星云科技",
                "title": "高级后端工程师",
                "start_date": "2022-03",
                "end_date": "至今",
                "is_current": True,
                "description": "负责核心交易系统的架构升级，将单体应用拆分为微服务架构，"
                             "引入消息队列和缓存机制，系统吞吐量提升 3 倍",
                "highlights": ["主导微服务拆分", "QPS 从 2000 提升至 8000"],
            },
            {
                "company": "云帆互联",
                "title": "后端开发工程师",
                "start_date": "2019-07",
                "end_date": "2022-02",
                "is_current": False,
                "description": "负责用户增长团队的后端开发，搭建用户行为分析平台",
                "highlights": ["日活用户从 10 万增长到 50 万"],
            },
        ],
        "education": [
            {"school": "华中科技大学", "degree": "本科", "major": "计算机科学与技术", "graduation_year": "2019"},
        ],
        "skills": [
            {"name": "Python", "level": "精通", "source": "简历"},
            {"name": "Go", "level": "精通", "source": "简历"},
            {"name": "MySQL", "level": "精通", "source": "简历"},
            {"name": "Redis", "level": "熟悉", "source": "简历"},
            {"name": "Docker", "level": "熟悉", "source": "简历"},
            {"name": "Kubernetes", "level": "熟悉", "source": "简历"},
        ],
    }

    status, data = api("POST", "/api/candidates", candidate)
    if status != 200:
        print(color(f"  ❌ 创建候选人失败: {data.get('error', '未知错误')}", "1;31"))
        return
    candidate_id = data["candidate"]["_id"]
    print(color(f"  ✅ 候选人已创建  ID: {candidate_id}", "1;32"))

    # ==================== 步骤 3: 启动面试 ====================
    print_step("🎙️", "步骤 3: 启动 AI 面试", "面试时长: 30 分钟 · 使用已创建的画像和简历")

    status, data = api("POST", "/api/interview/start", {
        "profile_id": profile_id,
        "candidate_id": candidate_id,
        "duration": 30,
    })
    if status != 200:
        err = data.get("error", "未知错误")
        if data.get("need_llm"):
            print(color(f"  ❌ {err}", "1;31"))
            print(color("  💡 请在页面底部配置 LLM 后重试", "1;33"))
        else:
            print(color(f"  ❌ 启动失败: {err}", "1;31"))
        return

    interview = data["interview"]
    interview_id = interview["interview_id"]
    plan = interview["plan"]
    generated_by = plan.get("_generated_by", "unknown")

    print(color(f"  ✅ 面试已启动  ID: {interview_id}", "1;32"))
    print(f"     生成方式: {color('大语言模型', '1;33') if generated_by == 'llm' else color('降级方案', '1;31')}")
    print(f"     面试环节: {len(plan['sections'])} 个")
    for sec in plan["sections"]:
        q_count = len(sec["questions"])
        print(f"       📂 {sec['section_name']}  ({sec['duration_minutes']}分钟, {q_count}个问题)")

    # ==================== 步骤 4: AI 自动问答 ====================
    print_step("💬", "步骤 4: AI 自动问答", "共 5 轮对话 · 每轮包含提问+回答+追问")

    elapsed = 0
    question_count = 0
    max_questions = 5
    total_dialogues = 0

    while question_count < max_questions:
        question_count += 1
        print()
        print(color(f"  ┌─── 第 {question_count} 轮 ──────────────────────────┐", "1;34"))

        # AI 提问
        status, data = api("POST", "/api/interview/next-question", {"elapsed_minutes": elapsed})
        if status != 200:
            print(color(f"  ⏹ 面试结束: 所有问题已问完", "1;33"))
            break

        question = data["question"]
        q_text = question["question_text"]
        q_cat = question.get("category", "技术")
        q_diff = question.get("difficulty", "中等")

        print_bubble("AI", f"[{q_cat} · {q_diff}]\n{q_text}", "1;36")

        # 候选人回答（根据问题类别和内容自动生成）
        answer = generate_mock_answer(q_text, q_cat)
        time.sleep(0.3)  # 模拟思考间隔
        print_bubble("候选人", answer, "1;33")

        # 提交回答
        status, resp_data = api("POST", "/api/interview/answer", {
            "question_id": question["question_id"],
            "answer": answer,
        })
        total_dialogues += 1

        # AI 追问
        result = resp_data.get("result", {})
        if result.get("follow_up"):
            time.sleep(0.5)
            follow_up = result["follow_up"]
            print_bubble("AI", f"💡 追问:\n{follow_up}", "1;35")

            # 回答追问
            follow_answer = generate_mock_answer(follow_up, q_cat)
            time.sleep(0.3)
            print_bubble("候选人", follow_answer, "1;33")

            # 提交追问回答
            api("POST", "/api/interview/ask-follow-up", {"question": follow_up})
            api("POST", "/api/interview/answer", {
                "question_id": question["question_id"],
                "answer": follow_answer,
            })
            total_dialogues += 1

        print(color(f"  └────────────────────────────────────────┘", "1;34"))
        elapsed += 5  # 每道题算 5 分钟

    # ==================== 步骤 5: 结束面试 ====================
    print_step("📊", "步骤 5: 结束面试并生成评估")

    status, data = api("POST", "/api/interview/end")
    if status != 200:
        print(color(f"  ❌ 结束面试失败: {data.get('error', '未知错误')}", "1;31"))
        return

    result = data["interview"]
    evaluation = result.get("evaluation", {})

    print(color(f"  ✅ 面试已结束", "1;32"))
    print(f"     状态: {result['status']}")
    print(f"     对话轮次: {total_dialogues} 次")
    print(f"     综合评分: {color(str(evaluation.get('overall_score', 'N/A')), '1;33')}")
    print(f"     推荐结论: {color(evaluation.get('recommendation', 'N/A'), '1;36')}")
    if evaluation.get("ai_comment"):
        print(f"     AI 评语: {evaluation['ai_comment'][:100]}...")

    # ==================== 最终总结 ====================
    print()
    print(color("=" * 58, "1;35"))
    print(color("  ✅  自动交互示例完成！", "1;32;7"))
    print(color("=" * 58, "1;35"))
    print()
    print(f"  面试记录 ID:  {color(interview_id, '1;33')}")
    print(f"  查看面试回放: {color(f'http://127.0.0.1:5000/interview/{interview_id}', '1;36')}")
    print(f"  查看记录列表: {color('http://127.0.0.1:5000/records', '1;36')}")
    print()


if __name__ == "__main__":
    main()
