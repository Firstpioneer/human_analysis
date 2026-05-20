"""LLM 配置路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.interview.llm_service import get_llm_service, reload_llm_service, LLMConfig

router = APIRouter()


class LLMConfigUpdateRequest(BaseModel):
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    provider: str = "openai"
    temperature: float = 0.7
    max_tokens: int = 2048


class LLMToggleRequest(BaseModel):
    enabled: bool = True


@router.get("/config")
async def get_config():
    llm_service = get_llm_service()
    return {"success": True, "config": llm_service.get_config()}


@router.post("/config")
async def update_config(request: LLMConfigUpdateRequest):
    config = request.model_dump()
    err = LLMConfig.validate(config)
    if err:
        raise HTTPException(status_code=400, detail=err)
    llm_service = reload_llm_service(config)
    return {"success": True, "config": llm_service.get_config()}


@router.post("/test")
async def test_connection():
    llm_service = get_llm_service()
    if not llm_service.is_available:
        raise HTTPException(status_code=400, detail="LLM 未配置或不可用")
    try:
        result = llm_service.chat(
            messages=[{"role": "user", "content": "请回复'连接成功'这四个字"}],
            system_prompt="你是一个测试助手",
            max_tokens=50,
        )
        if result:
            return {"success": True, "reply": result}
        raise HTTPException(status_code=500, detail="LLM 返回为空")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/toggle")
async def toggle_llm(request: LLMToggleRequest):
    from app.routers.interview import engine
    import app.routers.interview as interview_module
    interview_module.engine = __import__('app.services.interview.interview_engine',
                                          fromlist=['InterviewEngine']).InterviewEngine(use_llm=request.enabled)
    return {"success": True, "llm_enabled": request.enabled}
