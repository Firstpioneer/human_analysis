"""画像模块路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.models.portrait import (
    ChatRequest, ChatResponse, Message,
    GenerateProfileRequest, GenerateProfileResponse,
    SaveProfileRequest
)
from app.services.portrait.agent import RecruitmentAgent
from app.storage.portrait_store import (
    validate_profile, enrich_profile,
    save_profile, load_profile, list_profiles,
    save_conversation, load_conversation,
    delete_conversation, list_conversations
)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        agent = RecruitmentAgent(request.api_key)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"API Key 无效: {str(e)}")

    messages = request.messages
    conversation_id = request.conversation_id
    if not conversation_id:
        import uuid
        conversation_id = str(uuid.uuid4())

    last_user_msg = request.message
    PROFILE_KEYWORDS = [
        "生成画像", "生成人才画像", "开始生成", "输出画像",
        "画像生成", "人才画像", "生成一下", "可以生成",
        "确认生成", "开始画像", "输出人才", "生成吧",
        "整理画像", "汇总画像", "出画像",
        "帮我生成", "给我生成", "生成一个", "出一个画像",
    ]
    should_generate = request.generate_profile or any(kw in last_user_msg for kw in PROFILE_KEYWORDS)

    if should_generate:
        try:
            profile = agent.generate_profile(messages)
            if profile.get("generate_error"):
                reply = f"画像生成遇到问题：{profile.get('raw_text', '未知错误')}，请稍后重试或补充更多信息。"
                return ChatResponse(reply=reply, conversation_id=conversation_id,
                                    messages=messages, profile_draft=None, phase="clarify")
            else:
                profile = enrich_profile(profile)
                reply = "人才画像已生成！请在左侧查看预览，你可以要求修改任何部分，或者确认保存。"
                messages_data = [m.model_dump() for m in messages]
                save_conversation(conversation_id, messages_data, profile, profile.get("job_title", ""))
                return ChatResponse(reply=reply, conversation_id=conversation_id,
                                    messages=messages, profile_draft=profile, phase="generate")
        except Exception as e:
            reply = f"画像生成失败：{str(e)}，请稍后重试。"
            return ChatResponse(reply=reply, conversation_id=conversation_id,
                                messages=messages, profile_draft=None, phase="clarify")

    try:
        reply = agent.chat(messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"对话失败: {str(e)}")

    messages_data = [m.model_dump() for m in messages]
    messages_data.append({"role": "assistant", "content": reply, "timestamp": datetime.now().isoformat()})
    save_conversation(conversation_id, messages_data, None, "")

    return ChatResponse(reply=reply, conversation_id=conversation_id,
                        messages=messages, profile_draft=None, phase="clarify")


@router.post("/parse-jd")
async def parse_jd(request: ChatRequest):
    try:
        agent = RecruitmentAgent(request.api_key)
        result = agent.parse_jd(request.message)
        if result.get("parse_error"):
            return {"success": False, "raw_text": result.get("raw_text", ""), "error": "JD解析返回格式异常，请重试"}
        return {"success": True, "parsed": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"JD解析失败: {str(e)}")


@router.post("/generate-profile", response_model=GenerateProfileResponse)
async def generate_profile(request: GenerateProfileRequest):
    try:
        agent = RecruitmentAgent(request.api_key)
        profile = agent.generate_profile(request.messages)
        if profile.get("generate_error"):
            raw = profile.get('raw_text', '未知错误')
            snippet = raw[:200] + "..." if len(raw) > 200 else raw
            raise HTTPException(status_code=500, detail=f"AI未返回有效JSON，请重试。原始输出: {snippet}")
        profile = enrich_profile(profile)
        return GenerateProfileResponse(
            profile=profile,
            conversation_id=request.conversation_id or profile.get("id", "default")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"画像生成失败: {str(e)}")


@router.post("/save-profile")
async def save_profile_endpoint(request: SaveProfileRequest):
    profile = request.profile
    valid, errors = validate_profile(profile)
    if not valid:
        raise HTTPException(status_code=400, detail=f"画像验证失败: {'; '.join(errors)}")
    profile = enrich_profile(profile)
    profile["status"] = "confirmed"
    messages_data = [m.model_dump() for m in request.messages] if request.messages else []
    profile_id = save_profile(profile, messages_data)
    return {"success": True, "profile_id": profile_id, "message": "画像保存成功"}


@router.get("/profiles")
async def get_profiles():
    return {"profiles": list_profiles()}


@router.get("/profiles/{profile_id}")
async def get_profile(profile_id: str):
    profile = load_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="画像不存在")
    return profile


class SaveConversationRequest(BaseModel):
    conversation_id: Optional[str] = None
    messages: list[dict] = []
    profile_draft: Optional[dict] = None
    job_title: str = ""


@router.get("/conversations")
async def get_conversations():
    return {"conversations": list_conversations()}


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    conv = load_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    return conv


@router.post("/conversations")
async def save_conversation_endpoint(request: SaveConversationRequest):
    conv_id = save_conversation(
        request.conversation_id, request.messages,
        request.profile_draft, request.job_title
    )
    return {"success": True, "conversation_id": conv_id}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation_endpoint(conversation_id: str):
    success = delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="对话不存在")
    return {"success": True, "message": "对话已删除"}
