"""面试模块路由（Flask → FastAPI 迁移）"""
from fastapi import APIRouter, HTTPException

from app.models.interview import (
    StartInterviewRequest, NextQuestionRequest, AnswerRequest,
    FollowUpRequest, StatusRequest, ProfileRequest, CandidateRequest
)
from app.services.interview.interview_engine import InterviewEngine
from app.storage.interview_store import InterviewStorage, ProfileCandidateStorage

router = APIRouter()

engine = InterviewEngine()
storage = InterviewStorage()
pc_storage = ProfileCandidateStorage()

_interview_state = {"active": False, "elapsed_minutes": 0, "current_question_idx": 0}



@router.post("/start")
async def start_interview(request: StartInterviewRequest):
    profile = request.profile
    candidate = request.candidate
    if not profile and request.profile_id:
        profile = pc_storage.get_profile(request.profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="所选人才画像不存在，请重新选择")
    if not candidate and request.candidate_id:
        candidate = pc_storage.get_candidate(request.candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="所选简历分析结果不存在，请重新选择")
    if not profile or not candidate:
        raise HTTPException(status_code=400, detail="请先选择人才画像和简历分析结果，再开始 AI 面试")
    try:
        interview = engine.start_interview(profile=profile, candidate=candidate, total_duration=request.duration)
        _interview_state["active"] = True
        _interview_state["elapsed_minutes"] = 0
        _interview_state["current_question_idx"] = 0
        return {"success": True, "interview": interview}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/next-question")
async def next_question(request: NextQuestionRequest):
    question = engine.get_next_question(request.elapsed_minutes)
    if question:
        _interview_state["current_question_idx"] += 1
        return {"success": True, "question": question}
    raise HTTPException(status_code=404, detail="所有问题已问完")


@router.post("/answer")
async def process_answer(request: AnswerRequest):
    result = engine.process_answer(
        request.question_id,
        request.answer,
        is_follow_up_answer=request.is_follow_up_answer,
        elapsed_seconds=request.elapsed_seconds,
        client_latency_ms=request.client_latency_ms,
    )
    return {"success": True, "result": result}


@router.post("/ask-follow-up")
async def ask_follow_up(request: FollowUpRequest):
    result = engine.ask_follow_up(request.question)
    return {"success": True, "result": result}


@router.post("/end")
async def end_interview():
    result = engine.end_interview()
    _interview_state["active"] = False
    return {"success": True, "interview": result}


@router.post("/status")
async def interview_status(request: StatusRequest):
    time_status = engine.get_time_status(request.elapsed_minutes)
    current = engine.get_current_interview()
    return {
        "success": True,
        "time_status": time_status,
        "active": _interview_state["active"],
        "interview_id": current.get("interview_id") if current else None,
    }


@router.get("/list")
async def list_interviews():
    interviews = storage.list_interviews()
    return {"success": True, "interviews": interviews}


@router.get("/detail/{interview_id}")
async def get_interview(interview_id: str):
    interview = storage.get_interview(interview_id)
    if interview:
        return {"success": True, "interview": interview}
    raise HTTPException(status_code=404, detail="未找到")


@router.delete("/detail/{interview_id}")
async def delete_interview(interview_id: str):
    result = storage.delete_interview(interview_id)
    return {"success": result}


@router.post("/restart/{interview_id}")
async def restart_interview(interview_id: str):
    old = storage.get_interview(interview_id)
    if not old:
        raise HTTPException(status_code=404, detail="面试记录不存在")
    profile = old.get("_profile")
    candidate = old.get("_candidate")
    duration = old.get("_duration", 45)
    if not profile:
        raise HTTPException(status_code=400, detail="该记录不包含完整画像，无法重新开始")
    try:
        interview = engine.start_interview(profile=profile, candidate=candidate, total_duration=duration)
        _interview_state["active"] = True
        _interview_state["elapsed_minutes"] = 0
        _interview_state["current_question_idx"] = 0
        return {"success": True, "interview": interview}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 画像 API ====================

@router.get("/profiles")
async def list_profiles():
    profiles = pc_storage.list_profiles()
    return {"success": True, "profiles": profiles}


@router.post("/profiles")
async def create_profile(request: ProfileRequest):
    profile = pc_storage.save_profile(request.model_dump())
    return {"success": True, "profile": profile}


@router.get("/profiles/{profile_id}")
async def get_profile(profile_id: str):
    profile = pc_storage.get_profile(profile_id)
    if profile:
        return {"success": True, "profile": profile}
    raise HTTPException(status_code=404, detail="未找到")


@router.delete("/profiles/{profile_id}")
async def delete_profile(profile_id: str):
    result = pc_storage.delete_profile(profile_id)
    return {"success": result}


# ==================== 候选人 API ====================

@router.get("/candidates")
async def list_candidates():
    candidates = pc_storage.list_candidates()
    return {"success": True, "candidates": candidates}


@router.post("/candidates")
async def create_candidate(request: CandidateRequest):
    candidate = pc_storage.save_candidate(request.model_dump())
    return {"success": True, "candidate": candidate}


@router.get("/candidates/{candidate_id}")
async def get_candidate(candidate_id: str):
    candidate = pc_storage.get_candidate(candidate_id)
    if candidate:
        return {"success": True, "candidate": candidate}
    raise HTTPException(status_code=404, detail="未找到")


@router.delete("/candidates/{candidate_id}")
async def delete_candidate(candidate_id: str):
    result = pc_storage.delete_candidate(candidate_id)
    return {"success": result}
