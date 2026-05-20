"""简历模块路由"""
from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os

from app.services.resume.pipeline_engine import ResumePipelineEngine
from app.storage.resume_store import save_resume_result, load_resume_result, list_resume_results
from app.storage.interview_store import ProfileCandidateStorage

router = APIRouter()
engine = ResumePipelineEngine()
pc_storage = ProfileCandidateStorage()


def _resume_to_candidate(result: dict) -> dict:
    """将简历解析结果转换为面试引擎的 candidate 格式"""
    resume_id = result.get("resume_id", "unknown")
    name = os.path.splitext(resume_id)[0]
    parsed = result.get("parsed_data", {})
    experiences = []
    for exp in parsed.get("objective_experiences", []):
        confidence = "中"
        strength = exp.get("signal_strength", 3)
        if strength >= 4:
            confidence = "高"
        elif strength <= 2:
            confidence = "低"
        experiences.append({
            "company": exp.get("company", ""),
            "title": exp.get("title", ""),
            "description": exp.get("description", ""),
            "signal": {"type": "事实", "confidence": confidence, "evidence": ""},
            "highlights": []
        })
    skills = []
    for claim in parsed.get("claims", []):
        skills.append({
            "name": claim.get("content", ""),
            "level": "熟悉",
            "source": "简历声明"
        })
    contact = {}
    footprint = parsed.get("digital_footprint", {})
    if footprint.get("github_url"):
        contact["github"] = footprint["github_url"]
    external_profiles = {}
    if footprint.get("status") == "success":
        external_profiles["github_activity"] = f"{footprint.get('public_repos', 0)} repos, {footprint.get('followers', 0)} followers"
        external_profiles["top_languages"] = [lang[0] for lang in footprint.get("top_languages", [])]
    candidate = {
        "name": name,
        "contact": contact,
        "summary": "",
        "experiences": experiences,
        "skills": skills,
        "external_profiles": external_profiles,
        "_blind_spots": result.get("blind_spots", []),
        "_source": "resume_parser"
    }
    return candidate


@router.post("/parse")
async def parse_resume(file: UploadFile = File(...)):
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        result = engine.run_pipeline(file_path)
        if result.get("status") == "success":
            save_resume_result(result)
            candidate = _resume_to_candidate(result)
            saved_candidate = pc_storage.save_candidate(candidate)
            result["candidate_id"] = saved_candidate.get("_id")
        return result
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@router.get("/results")
async def list_results():
    return {"results": list_resume_results()}


@router.get("/results/{resume_id}")
async def get_result(resume_id: str):
    result = load_resume_result(resume_id)
    if not result:
        raise HTTPException(status_code=404, detail="简历解析结果不存在")
    return result
