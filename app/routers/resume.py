"""简历模块路由"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
import shutil
import os
import uuid

from app.converters.candidate_converter import resume_to_interview_candidate
from app.services.resume.career_profile_service import CareerProfileService
from app.services.resume.pipeline_engine import ResumePipelineEngine
from app.storage.resume_store import save_resume_result, load_resume_result, list_resume_results, delete_resume_result
from app.storage.career_profile_store import (
    save_career_profile,
    load_career_profile,
    list_career_profiles,
    delete_career_profile,
)
from app.storage.interview_store import ProfileCandidateStorage

router = APIRouter()
engine = ResumePipelineEngine()
pc_storage = ProfileCandidateStorage()
career_service = CareerProfileService()


class CareerProfileCreateRequest(BaseModel):
    requirement_text: str

@router.post("/parse")
async def parse_resume(file: UploadFile = File(...)):
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    original_filename = os.path.basename(file.filename or "resume")
    ext = os.path.splitext(original_filename)[1].lower()
    allowed_exts = {".pdf", ".docx", ".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"不支持的简历格式: {ext or '未知'}")
    file_path = os.path.join(temp_dir, f"{uuid.uuid4().hex}{ext}")
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        result = engine.run_pipeline(file_path, original_filename=original_filename)
        if result.get("status") == "success":
            candidate = resume_to_interview_candidate(result)
            candidate["_resume_id"] = result.get("resume_id", "")
            saved_candidate = pc_storage.save_candidate(candidate)
            result["candidate_id"] = saved_candidate.get("_id")
            save_resume_result(result)
        return result
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@router.post("/career-profiles")
async def create_career_profile(request: CareerProfileCreateRequest):
    try:
        profile = career_service.normalize_requirement(request.requirement_text)
        saved = save_career_profile(profile)
        return {"success": True, "profile": saved}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"职业画像保存失败: {str(e)}")


@router.get("/career-profiles")
async def get_career_profiles():
    return {"profiles": list_career_profiles()}


@router.get("/career-profiles/{profile_id}")
async def get_career_profile(profile_id: str):
    profile = load_career_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="职业画像不存在")
    return profile


@router.delete("/career-profiles/{profile_id}")
async def delete_career_profile_endpoint(profile_id: str):
    if not delete_career_profile(profile_id):
        raise HTTPException(status_code=404, detail="职业画像不存在")
    return {"success": True, "message": "删除成功", "profile_id": profile_id}


@router.get("/results")
async def list_results():
    return {"results": list_resume_results()}


@router.get("/results/{resume_id}")
async def get_result(resume_id: str):
    result = load_resume_result(resume_id)
    if not result:
        raise HTTPException(status_code=404, detail="简历解析结果不存在")
    return result


@router.delete("/results/{resume_id}")
async def delete_result(resume_id: str):
    if not delete_resume_result(resume_id):
        raise HTTPException(status_code=404, detail="简历解析结果不存在")
    return {"message": "删除成功", "resume_id": resume_id}
