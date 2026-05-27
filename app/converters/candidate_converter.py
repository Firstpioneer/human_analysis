"""resume 输出 → interview candidate_schema 格式转换"""
import os
import uuid
from datetime import datetime


def resume_to_interview_candidate(result: dict) -> dict:
    """将 resume 解析结果转换为 interview 的 candidate_schema 格式"""
    resume_id = result.get("resume_id", "unknown")
    parsed = result.get("parsed_data", {})
    name = parsed.get("name") or os.path.splitext(result.get("source_filename") or resume_id)[0]

    # 转换 experiences
    experiences = []
    for exp in parsed.get("objective_experiences", []):
        strength = exp.get("signal_strength", 3)
        confidence = round(max(1, min(5, strength)) / 5, 2)
        experiences.append({
            "company": exp.get("company", ""),
            "title": exp.get("title", ""),
            "start_date": exp.get("start_date", ""),
            "end_date": exp.get("end_date", ""),
            "is_current": not exp.get("end_date"),
            "description": exp.get("description", ""),
            "signal": {"type": "事实", "confidence": confidence, "evidence": exp.get("description", "")[:160]},
            "highlights": exp.get("highlights", []),
            "source_type": "resume",
        })

    # 转换 claims → skills
    skills = []
    for claim in parsed.get("claims", []):
        skills.append({
            "name": claim.get("content", ""),
            "level": "熟悉",
            "source": "简历声明"
        })

    # 联系方式
    contact = parsed.get("contact", {}) or {}
    footprint = parsed.get("digital_footprint", {})
    if footprint.get("github_url"):
        contact["github"] = footprint["github_url"]
    blogs = footprint.get("blogs") or []
    if blogs and not contact.get("blog"):
        contact["blog"] = blogs[0].get("url", "")

    # 外部档案
    external_profiles = {}
    if footprint.get("status") == "success":
        external_profiles["github_activity"] = (
            f"{footprint.get('public_repos', 0)} repos, "
            f"{footprint.get('followers', 0)} followers"
        )
        external_profiles["top_languages"] = [
            lang[0] for lang in footprint.get("top_languages", [])
        ]
        external_profiles["recent_repositories"] = [
            repo.get("name") for repo in footprint.get("recent_repositories", [])[:5] if repo.get("name")
        ]
    if blogs:
        external_profiles["blog_articles"] = [
            blog.get("title") or blog.get("url") for blog in blogs if blog.get("status") == "success"
        ]

    candidate = {
        "_id": f"CAN_{uuid.uuid4().hex[:8].upper()}",
        "_created_at": datetime.now().isoformat(),
        "_updated_at": datetime.now().isoformat(),
        "name": name,
        "contact": contact,
        "summary": "",
        "experiences": experiences,
        "education": [],
        "skills": skills,
        "external_profiles": external_profiles,
        "_blind_spots": result.get("blind_spots", []),
        "_source": "resume_parser"
    }
    return candidate
