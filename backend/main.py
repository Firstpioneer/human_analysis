from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os

from models import (
    ChatRequest, ChatResponse, Message,
    GenerateProfileRequest, GenerateProfileResponse,
    SaveProfileRequest
)
from agent import RecruitmentAgent
from profile_generator import (
    validate_profile, enrich_profile,
    save_profile, load_profile, list_profiles
)
from conversation_store import (
    save_conversation, load_conversation,
    delete_conversation, list_conversations
)

app = FastAPI(title="AI招聘画像系统 - 需求Agent")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 提供前端静态文件
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


# ============================================================
# 对话接口
# ============================================================

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """主对话接口"""
    try:
        agent = RecruitmentAgent(request.api_key)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"API Key 无效: {str(e)}")

    # 前端已包含完整消息历史（含用户消息），直接使用
    messages = request.messages
    conversation_id = request.conversation_id

    # 只在真正没有 conversation_id 时才创建新的
    if not conversation_id:
        import uuid
        conversation_id = str(uuid.uuid4())

    # 检查是否是生成画像的指令
    # 方式1：前端显式标记
    # 方式2：关键词匹配（扩展关键词列表）
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
                # 画像生成失败，给用户明确提示，不回退到普通对话
                reply = f"画像生成遇到问题：{profile.get('raw_text', '未知错误')}，请稍后重试或补充更多信息。"
                return ChatResponse(
                    reply=reply,
                    conversation_id=conversation_id,
                    messages=messages,
                    profile_draft=None,
                    phase="clarify"
                )
            else:
                profile = enrich_profile(profile)
                reply = "人才画像已生成！请在左侧查看预览，你可以要求修改任何部分，或者确认保存。"
                # 自动保存对话（含画像）
                messages_data = [m.model_dump() for m in messages]
                save_conversation(conversation_id, messages_data, profile, profile.get("job_title", ""))
                return ChatResponse(
                    reply=reply,
                    conversation_id=conversation_id,
                    messages=messages,
                    profile_draft=profile,
                    phase="generate"
                )
        except Exception as e:
            # 画像生成异常，给用户明确提示，不回退到普通对话
            reply = f"画像生成失败：{str(e)}，请稍后重试。"
            return ChatResponse(
                reply=reply,
                conversation_id=conversation_id,
                messages=messages,
                profile_draft=None,
                phase="clarify"
            )

    # 普通对话
    try:
        reply = agent.chat(messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"对话失败: {str(e)}")

    # 自动保存对话（含助手回复）
    messages_data = [m.model_dump() for m in messages]
    # 手动追加助手回复用于保存
    messages_data.append({"role": "assistant", "content": reply, "timestamp": datetime.now().isoformat()})
    save_conversation(conversation_id, messages_data, None, "")

    return ChatResponse(
        reply=reply,
        conversation_id=conversation_id,
        messages=messages,
        profile_draft=None,
        phase="clarify"
    )


@app.post("/api/parse-jd")
async def parse_jd(request: ChatRequest):
    """解析JD文本"""
    try:
        agent = RecruitmentAgent(request.api_key)
        result = agent.parse_jd(request.message)
        if result.get("parse_error"):
            return {
                "success": False,
                "raw_text": result.get("raw_text", ""),
                "error": "JD解析返回格式异常，请重试"
            }
        return {"success": True, "parsed": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"JD解析失败: {str(e)}")


@app.post("/api/generate-profile", response_model=GenerateProfileResponse)
async def generate_profile(request: GenerateProfileRequest):
    """基于对话历史生成完整画像"""
    try:
        agent = RecruitmentAgent(request.api_key)
        profile = agent.generate_profile(request.messages)

        if profile.get("generate_error"):
            raw = profile.get('raw_text', '未知错误')
            # 截取前200字符作为错误提示
            snippet = raw[:200] + "..." if len(raw) > 200 else raw
            raise HTTPException(
                status_code=500,
                detail=f"AI未返回有效JSON，请重试。原始输出: {snippet}"
            )

        profile = enrich_profile(profile)

        return GenerateProfileResponse(
            profile=profile,
            conversation_id=request.conversation_id or profile.get("id", "default")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"画像生成失败: {str(e)}")


# ============================================================
# 画像保存/加载（正式保存用）
# ============================================================

@app.post("/api/save-profile")
async def save_profile_endpoint(request: SaveProfileRequest):
    """正式保存画像到画像库（含对话记录）"""
    profile = request.profile
    valid, errors = validate_profile(profile)
    if not valid:
        raise HTTPException(status_code=400, detail=f"画像验证失败: {'; '.join(errors)}")

    profile = enrich_profile(profile)
    profile["status"] = "confirmed"
    messages_data = [m.model_dump() for m in request.messages] if request.messages else []
    profile_id = save_profile(profile, messages_data)
    return {"success": True, "profile_id": profile_id, "message": "画像保存成功"}


@app.get("/api/profiles")
async def get_profiles():
    """列出所有已保存画像"""
    return {"profiles": list_profiles()}


@app.get("/api/profiles/{profile_id}")
async def get_profile(profile_id: str):
    """获取指定画像"""
    profile = load_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="画像不存在")
    return profile


# ============================================================
# 对话历史管理
# ============================================================

class SaveConversationRequest(BaseModel):
    conversation_id: Optional[str] = None
    messages: list[dict] = []
    profile_draft: Optional[dict] = None
    job_title: str = ""


@app.get("/api/conversations")
async def get_conversations():
    """列出所有对话历史"""
    return {"conversations": list_conversations()}


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """获取指定对话（含消息和画像草稿）"""
    conv = load_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    return conv


@app.post("/api/conversations")
async def save_conversation_endpoint(request: SaveConversationRequest):
    """手动保存/更新对话"""
    conv_id = save_conversation(
        request.conversation_id,
        request.messages,
        request.profile_draft,
        request.job_title
    )
    return {"success": True, "conversation_id": conv_id}


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation_endpoint(conversation_id: str):
    """删除指定对话"""
    success = delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="对话不存在")
    return {"success": True, "message": "对话已删除"}


@app.get("/api/health")
async def health():
    return {"status": "ok", "message": "AI招聘画像系统运行正常"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
