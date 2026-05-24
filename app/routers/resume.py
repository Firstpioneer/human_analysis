"""简历模块路由"""
from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os

from app.converters.candidate_converter import resume_to_interview_candidate
from app.services.resume.pipeline_engine import ResumePipelineEngine
from app.storage.resume_store import save_resume_result, load_resume_result, list_resume_results, delete_resume_result
from app.storage.interview_store import ProfileCandidateStorage

router = APIRouter()
engine = ResumePipelineEngine()
pc_storage = ProfileCandidateStorage()

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
            candidate = resume_to_interview_candidate(result)
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


@router.delete("/results/{resume_id}")
async def delete_result(resume_id: str):
    if not delete_resume_result(resume_id):
        raise HTTPException(status_code=404, detail="简历解析结果不存在")
    return {"message": "删除成功", "resume_id": resume_id}
