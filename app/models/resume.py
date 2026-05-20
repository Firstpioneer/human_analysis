"""简历模块数据模型"""
from pydantic import BaseModel
from typing import Optional


class ResumeParseResult(BaseModel):
    resume_id: str
    status: str
    parsed_data: dict
    blind_spots: list[str] = []
