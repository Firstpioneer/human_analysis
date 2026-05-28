"""portrait JobProfile → interview profile_schema 格式转换"""
import uuid
from datetime import datetime


def portrait_to_interview_profile(portrait: dict) -> dict:
    """将 portrait 的 JobProfile 转换为 interview 的 profile_schema 格式

    转换是有损的，portrait 的丰富信息通过扩展字段保留。
    """
    job_title = portrait.get("job_title", "")
    core_roles = portrait.get("core_roles", [])
    department = core_roles[0].get("description", "") if core_roles else ""

    # 展开 signal_dimensions → skills
    skills = []
    for category in portrait.get("signal_dimensions", []):
        for dim in category.get("dimensions", []):
            weight_str = dim.get("weight", "参考")
            if weight_str == "核心":
                level, weight = "精通", 8
            elif weight_str == "重要":
                level, weight = "熟悉", 5
            else:
                level, weight = "了解", 3
            skills.append({
                "name": dim.get("name", ""),
                "level": level,
                "weight": weight
            })

    soft_skills = list(portrait.get("must_have", []))

    profile = {
        "_id": f"PRO_{uuid.uuid4().hex[:8].upper()}",
        "_created_at": datetime.now().isoformat(),
        "_updated_at": datetime.now().isoformat(),
        "position": {
            "title": job_title,
            "department": department,
            "level": "中级",
            "salary_range": ""
        },
        "requirements": {
            "education": {"min_degree": "不限", "preferred_majors": []},
            "experience": {"min_years": 0, "preferred_industries": []},
            "skills": skills,
            "soft_skills": soft_skills
        },
        "qualifications": {"certifications": [], "projects": [], "other": []},
        "culture_fit": {"team_size": "", "work_style": "", "values": []},
        # 扩展字段 - 保留 portrait 丰富信息
        "_signal_dimensions": portrait.get("signal_dimensions", []),
        "_company_context": portrait.get("company_context", {}),
        "_core_roles": core_roles,
        "_must_have": portrait.get("must_have", []),
        "_nice_to_have": portrait.get("nice_to_have", []),
        "_anti_profile": portrait.get("anti_profile", []),
        "_general_questions": portrait.get("general_questions", []),
        "_conversation_summary": portrait.get("conversation_summary", ""),
        "_source": "portrait"
    }
    return profile
