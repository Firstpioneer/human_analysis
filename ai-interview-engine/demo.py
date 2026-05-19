"""
AI 面试引擎 - 命令行 Demo
无需启动 Web 服务器，直接验证核心功能
"""

import json
from modules.interview_engine import InterviewEngine
from modules.storage import InterviewStorage
from modules.question_generator import QuestionGenerator
from modules.follow_up_strategy import FollowUpStrategy, TimeController


def print_separator(title):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def demo_question_generation():
    """演示 1: 面试问题方案自动生成"""
    print_separator("演示 1: 面试问题方案自动生成")

    profile = {
        "position": {"title": "高级后端开发工程师", "department": "技术部", "level": "高级"},
        "requirements": {
            "skills": [
                {"name": "Python", "level": "精通", "weight": 10},
                {"name": "Flask", "level": "精通", "weight": 9},
                {"name": "MySQL", "level": "熟悉", "weight": 8},
                {"name": "Redis", "level": "熟悉", "weight": 7},
                {"name": "Docker", "level": "熟悉", "weight": 6},
            ],
            "soft_skills": ["团队协作", "沟通表达"],
        },
    }

    generator = QuestionGenerator()

    try:
        plan = generator.generate_plan(profile, total_duration_minutes=45)
    except RuntimeError as e:
        print(f"  ⚠️ {e}")
        print()
        print("  💡 请在浏览器中打开页面，在底部「大语言模型配置」面板中填写配置。")
        print("  ℹ️ 演示 4 的完整面试流程也将跳过（原因相同）。")
        print()
        print("⏭ 已跳过（需配置 LLM）")
        return None

    print(f"面试总时长: {plan['total_duration_minutes']} 分钟")
    print(f"面试环节数: {len(plan['sections'])}")
    print()

    for section in plan["sections"]:
        print(f"  📂 {section['section_name']} ({section['duration_minutes']}分钟)")
        for q in section["questions"]:
            print(f"    [{q['difficulty']}] {q['question_text'][:60]}...")
        print()

    print("✅ 面试方案自动生成成功！")
    return plan


def demo_follow_up_strategy():
    """演示 2: 追问策略"""
    print_separator("演示 2: 追问策略")

    strategy = FollowUpStrategy()

    test_cases = [
        ("具体实现", "我用 Python 写了一个高性能的 API 网关", "触发'具体实现'关键词"),
        ("优化", "我对数据库查询做了优化，加了索引", "触发'优化'关键词"),
        ("数据", "QPS 从 1000 提升到了 5000", "触发'数据'关键词"),
        ("通用", "是的，我做过类似的项目", "短回答触发通用追问"),
    ]

    for trigger, answer, desc in test_cases:
        follow_up = strategy.generate_follow_up([trigger], answer)
        print(f"  候选人说: \"{answer}\"")
        print(f"  场景: {desc}")
        print(f"  AI 追问: \"{follow_up}\"")
        print()

    print("✅ 追问策略运行正常！")


def demo_time_control():
    """演示 3: 时间控制"""
    print_separator("演示 3: 时间控制")

    plan = {
        "sections": [
            {"section_name": "技术考察", "duration_minutes": 20},
            {"section_name": "项目经验", "duration_minutes": 12},
            {"section_name": "软技能与文化", "duration_minutes": 8},
            {"section_name": "候选人提问", "duration_minutes": 5},
        ]
    }

    timer = TimeController()
    timer.start_interview(plan)

    checkpoints = [0, 10, 22, 35, 41, 44]

    for minutes in checkpoints:
        section = timer.get_current_section(minutes)
        remaining = timer.get_remaining_time(minutes)
        progress = timer.get_section_progress(minutes, section["section_name"]) if section else 0
        action = timer.suggest_next_action(minutes, 3, 8)

        print(f"  ⏱ 第 {minutes:2d} 分钟:")
        print(f"     当前环节: {section['section_name'] if section else '无'}")
        print(f"     环节进度: {progress:.0%}")
        print(f"     剩余时间: {remaining:.0f} 分钟")
        print(f"     建议动作: {action}")
        print()

    print("✅ 时间控制运行正常！")


def demo_full_interview():
    """演示 4: 完整面试流程"""
    print_separator("演示 4: 完整 AI 面试流程")

    engine = InterviewEngine()

    # 1. 创建画像
    profile = {
        "position": {"title": "中级前端工程师", "department": "前端组", "level": "中级"},
        "requirements": {
            "skills": [
                {"name": "JavaScript", "level": "精通", "weight": 10},
                {"name": "React", "level": "精通", "weight": 9},
                {"name": "TypeScript", "level": "熟悉", "weight": 7},
            ],
            "soft_skills": ["沟通协作"],
        },
    }

    candidate = {
        "name": "张三",
        "experiences": [
            {
                "company": "某科技公司",
                "title": "前端开发",
                "description": "负责核心业务前端开发",
            }
        ],
    }

    # 2. 开始面试
    print(">>> 开始面试...")
    try:
        interview = engine.start_interview(profile, candidate, total_duration=30)
    except RuntimeError as e:
        print(f"  ⚠️ {e}")
        print()
        print("  💡 配置 LLM 后即可运行完整面试流程。")
        print()
        print("⏭ 已跳过（需配置 LLM）")
        return None
    print(f"    面试 ID: {interview['interview_id']}")
    print(f"    面试方案: {len(interview['plan']['sections'])} 个环节")
    print()

    # 3. 模拟问答
    elapsed = 0
    question_count = 0
    max_questions = 5

    while question_count < max_questions:
        question = engine.get_next_question(elapsed)
        if not question:
            print("    所有问题已问完")
            break

        question_count += 1
        print(f"  🤖 Q{question_count}: {question['question_text'][:60]}...")

        # 模拟回答
        mock_answer = f"关于这个问题，我有丰富的经验。在过去的项目中，我深入使用相关技术，解决了多个实际业务场景中的挑战。具体来说，我采用了最佳实践方案，并取得了很好的效果。"
        print(f"  👤 答: {mock_answer[:40]}...")

        result = engine.process_answer(question["question_id"], mock_answer)
        if result.get("follow_up"):
            print(f"  💡 AI 追问: {result['follow_up']}")
            engine.ask_follow_up(result["follow_up"])

        elapsed += 5  # 每道题算5分钟
        print()

    # 4. 结束面试
    print(">>> 结束面试...")
    result = engine.end_interview()
    print(f"    状态: {result['status']}")
    print(f"    对话轮次: {len(result['dialogues'])}")
    print(f"    综合评分: {result['evaluation']['overall_score']}")
    print()

    print("✅ 完整面试流程运行成功！")
    return result


def main():
    print("╔══════════════════════════════════════════════╗")
    print("║        AI 面试引擎 v1.0 - 功能演示           ║")
    print("╚══════════════════════════════════════════════╝")

    demo_question_generation()
    demo_follow_up_strategy()
    demo_time_control()
    demo_full_interview()

    print_separator("全部演示完成")
    print("  启动 Web 服务: python app.py")
    print("  访问地址: http://127.0.0.1:5000")


if __name__ == "__main__":
    main()
