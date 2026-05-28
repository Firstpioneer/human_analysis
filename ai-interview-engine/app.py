"""
AI 面试引擎 - Flask Web 应用
提供完整的 AI 对话面试体验
"""

import json
import os
import threading
from datetime import datetime

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_from_directory,
)

from modules.interview_engine import InterviewEngine
from modules.storage import InterviewStorage, ProfileCandidateStorage
from modules.llm_service import get_llm_service, reload_llm_service, LLMConfig

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(24).hex()

# 全局实例
engine = InterviewEngine()
storage = InterviewStorage()
pc_storage = ProfileCandidateStorage()
llm_service = get_llm_service()

# 模拟的面试时间跟踪（实际由前端报告）
_interview_state = {
    "active": False,
    "elapsed_minutes": 0,
    "current_question_idx": 0,
}


# ==================== 页面路由 ====================


@app.route("/")
def index():
    """首页"""
    return render_template("index.html")


@app.route("/interview/<interview_id>")
def interview_room(interview_id):
    """面试房间"""
    interview = storage.get_interview(interview_id)
    if not interview:
        return render_template("index.html", error="面试记录不存在")
    return render_template(
        "interview.html",
        interview=interview,
        interview_json=json.dumps(interview, ensure_ascii=False),
    )


@app.route("/records")
def interview_records():
    """面试记录列表"""
    interviews = storage.list_interviews()
    return render_template("records.html", interviews=interviews)


# ==================== API 接口 ====================


@app.route("/api/interview/start", methods=["POST"])
def api_start_interview():
    """开始新面试"""
    data = request.get_json() or {}
    profile = data.get("profile")
    candidate = data.get("candidate")
    profile_id = data.get("profile_id")
    candidate_id = data.get("candidate_id")

    # 支持按 ID 引用已存储的画像/简历
    if not profile and profile_id:
        profile = pc_storage.get_profile(profile_id)
    if not candidate and candidate_id:
        candidate = pc_storage.get_candidate(candidate_id)

    if not profile:
        # 使用默认画像（Demo模式）
        profile = _default_profile()

    duration = data.get("duration", 45)

    try:
        interview = engine.start_interview(
            profile=profile,
            candidate=candidate,
            total_duration=duration,
        )
        _interview_state["active"] = True
        _interview_state["elapsed_minutes"] = 0
        _interview_state["current_question_idx"] = 0
        return jsonify({"success": True, "interview": interview})
    except RuntimeError as e:
        return jsonify({"success": False, "error": str(e), "need_llm": True}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/interview/next-question", methods=["POST"])
def api_next_question():
    """获取下一问题"""
    data = request.get_json() or {}
    elapsed = data.get("elapsed_minutes", 0)

    question = engine.get_next_question(elapsed)
    if question:
        _interview_state["current_question_idx"] += 1
        return jsonify({"success": True, "question": question})
    else:
        return jsonify({"success": False, "message": "所有问题已问完"}), 404


@app.route("/api/interview/answer", methods=["POST"])
def api_process_answer():
    """处理回答"""
    data = request.get_json() or {}
    question_id = data.get("question_id", "")
    answer = data.get("answer", "")

    result = engine.process_answer(question_id, answer)
    return jsonify({"success": True, "result": result})


@app.route("/api/interview/ask-follow-up", methods=["POST"])
def api_ask_follow_up():
    """AI 发出追问"""
    data = request.get_json() or {}
    question = data.get("question", "")

    result = engine.ask_follow_up(question)
    return jsonify({"success": True, "result": result})


@app.route("/api/interview/end", methods=["POST"])
def api_end_interview():
    """结束面试"""
    result = engine.end_interview()
    _interview_state["active"] = False
    return jsonify({"success": True, "interview": result})


@app.route("/api/interview/status", methods=["POST"])
def api_interview_status():
    """获取面试状态"""
    data = request.get_json() or {}
    elapsed = data.get("elapsed_minutes", 0)
    time_status = engine.get_time_status(elapsed)
    current = engine.get_current_interview()
    return jsonify(
        {
            "success": True,
            "time_status": time_status,
            "active": _interview_state["active"],
            "interview_id": current.get("interview_id") if current else None,
        }
    )


@app.route("/api/interviews")
def api_list_interviews():
    """获取面试列表"""
    interviews = storage.list_interviews()
    return jsonify({"success": True, "interviews": interviews})


@app.route("/api/interview/<interview_id>")
def api_get_interview(interview_id):
    """获取面试详情"""
    interview = storage.get_interview(interview_id)
    if interview:
        return jsonify({"success": True, "interview": interview})
    return jsonify({"success": False, "error": "未找到"}), 404


@app.route("/api/interview/<interview_id>", methods=["DELETE"])
def api_delete_interview(interview_id):
    """删除面试记录"""
    result = storage.delete_interview(interview_id)
    return jsonify({"success": result})


@app.route("/api/interview/<interview_id>/restart", methods=["POST"])
def api_restart_interview(interview_id):
    """基于已有面试记录重新开始一场面试"""
    old = storage.get_interview(interview_id)
    if not old:
        return jsonify({"success": False, "error": "面试记录不存在"}), 404

    # 从旧记录中提取画像和候选人数据
    profile = old.get("_profile")
    candidate = old.get("_candidate")
    duration = old.get("_duration", 45)

    if not profile:
        return jsonify({"success": False, "error": "该记录不包含完整画像，无法重新开始"}), 400

    try:
        interview = engine.start_interview(
            profile=profile,
            candidate=candidate,
            total_duration=duration,
        )
        _interview_state["active"] = True
        _interview_state["elapsed_minutes"] = 0
        _interview_state["current_question_idx"] = 0
        return jsonify({"success": True, "interview": interview})
    except RuntimeError as e:
        return jsonify({"success": False, "error": str(e), "need_llm": True}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== 人才画像 API (对接方向一) ====================


@app.route("/api/profiles", methods=["GET"])
def api_list_profiles():
    """获取人才画像列表"""
    profiles = pc_storage.list_profiles()
    return jsonify({"success": True, "profiles": profiles})


@app.route("/api/profiles", methods=["POST"])
def api_create_profile():
    """创建/更新人才画像"""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "请求体为空"}), 400
    if "position" not in data or "requirements" not in data:
        return jsonify({"success": False, "error": "缺少必要字段(position, requirements)"}), 400

    profile = pc_storage.save_profile(data)
    return jsonify({"success": True, "profile": profile})


@app.route("/api/profiles/<profile_id>", methods=["GET"])
def api_get_profile(profile_id):
    """获取单个人才画像"""
    profile = pc_storage.get_profile(profile_id)
    if profile:
        return jsonify({"success": True, "profile": profile})
    return jsonify({"success": False, "error": "未找到"}), 404


@app.route("/api/profiles/<profile_id>", methods=["DELETE"])
def api_delete_profile(profile_id):
    """删除人才画像"""
    result = pc_storage.delete_profile(profile_id)
    return jsonify({"success": result})


# ==================== 候选人档案 API (对接方向二) ====================


@app.route("/api/candidates", methods=["GET"])
def api_list_candidates():
    """获取候选人档案列表"""
    candidates = pc_storage.list_candidates()
    return jsonify({"success": True, "candidates": candidates})


@app.route("/api/candidates", methods=["POST"])
def api_create_candidate():
    """创建/更新候选人档案"""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "请求体为空"}), 400
    if "name" not in data or "experiences" not in data:
        return jsonify({"success": False, "error": "缺少必要字段(name, experiences)"}), 400

    candidate = pc_storage.save_candidate(data)
    return jsonify({"success": True, "candidate": candidate})


@app.route("/api/candidates/<candidate_id>", methods=["GET"])
def api_get_candidate(candidate_id):
    """获取单个候选人档案"""
    candidate = pc_storage.get_candidate(candidate_id)
    if candidate:
        return jsonify({"success": True, "candidate": candidate})
    return jsonify({"success": False, "error": "未找到"}), 404


@app.route("/api/candidates/<candidate_id>", methods=["DELETE"])
def api_delete_candidate(candidate_id):
    """删除候选人档案"""
    result = pc_storage.delete_candidate(candidate_id)
    return jsonify({"success": result})


# ==================== LLM 配置接口 ====================


@app.route("/api/llm/config", methods=["GET"])
def api_llm_get_config():
    """获取 LLM 配置状态"""
    return jsonify({"success": True, "config": llm_service.get_config()})


@app.route("/api/llm/config", methods=["POST"])
def api_llm_update_config():
    """更新 LLM 配置"""
    data = request.get_json() or {}
    config = {
        "api_key": data.get("api_key", ""),
        "base_url": data.get("base_url", "https://api.openai.com/v1"),
        "model": data.get("model", "gpt-4o-mini"),
        "provider": data.get("provider", "openai"),
        "temperature": float(data.get("temperature", 0.7)),
        "max_tokens": int(data.get("max_tokens", 2048)),
    }

    err = LLMConfig.validate(config)
    if err:
        return jsonify({"success": False, "error": err}), 400

    global llm_service
    llm_service = reload_llm_service(config)
    return jsonify({"success": True, "config": llm_service.get_config()})


@app.route("/api/llm/test", methods=["POST"])
def api_llm_test():
    """测试 LLM 连接"""
    if not llm_service.is_available:
        return jsonify({"success": False, "error": "LLM 未配置或不可用"}), 400

    try:
        result = llm_service.chat(
            messages=[{"role": "user", "content": "请回复'连接成功'这四个字"}],
            system_prompt="你是一个测试助手",
            max_tokens=50,
        )
        if result:
            return jsonify({"success": True, "reply": result})
        return jsonify({"success": False, "error": "LLM 返回为空"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/llm/toggle", methods=["POST"])
def api_llm_toggle():
    """切换 LLM 启用/禁用"""
    data = request.get_json() or {}
    enabled = data.get("enabled", True)

    # 重新创建引擎（带/不带 LLM）
    global engine
    engine = InterviewEngine(use_llm=enabled)
    return jsonify({"success": True, "llm_enabled": enabled})


# ==================== 辅助函数 ====================


def _default_profile():
    """默认人才画像（Demo用）"""
    return {
        "position": {
            "title": "高级后端开发工程师",
            "department": "技术部",
            "level": "高级",
            "salary_range": "25K-40K",
        },
        "requirements": {
            "education": {
                "min_degree": "本科",
                "preferred_majors": ["计算机科学", "软件工程"],
            },
            "experience": {
                "min_years": 3,
                "preferred_industries": ["互联网", "科技"],
            },
            "skills": [
                {"name": "Python", "level": "精通", "weight": 10},
                {"name": "Flask/FastAPI", "level": "精通", "weight": 9},
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


if __name__ == "__main__":
    print("=" * 50)
    print("  AI 面试引擎 v1.0")
    print("=" * 50)
    print(f"  启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  访问地址: http://127.0.0.1:5000")
    print(f"  面试记录: ./data/records/")
    print("=" * 50)
    app.run(debug=True, host="127.0.0.1", port=5000)
