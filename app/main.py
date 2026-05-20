"""FastAPI 应用工厂"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.routers import portrait, resume, interview, llm_config


def create_app() -> FastAPI:
    app = FastAPI(title="AI 招聘评估系统", version="1.0")

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(portrait.router, prefix="/api/portrait", tags=["画像"])
    app.include_router(resume.router, prefix="/api/resume", tags=["简历"])
    app.include_router(interview.router, prefix="/api/interview", tags=["面试"])
    app.include_router(llm_config.router, prefix="/api/llm", tags=["LLM配置"])

    # 挂载前端静态文件
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
    if os.path.exists(frontend_dir):
        app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    # SPA 入口 - 所有非 API 路由返回 index.html
    @app.get("/")
    async def serve_index():
        index_path = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "AI 招聘评估系统 API", "docs": "/docs"}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
