"""面试模块数据模型"""
from pydantic import BaseModel
from typing import Optional


class StartInterviewRequest(BaseModel):
    profile: Optional[dict] = None
    candidate: Optional[dict] = None
    profile_id: Optional[str] = None
    candidate_id: Optional[str] = None
    duration: int = 45


class NextQuestionRequest(BaseModel):
    elapsed_minutes: float = 0


class AnswerRequest(BaseModel):
    question_id: str
    answer: str
    is_follow_up_answer: bool = False
    elapsed_seconds: Optional[int] = None
    client_latency_ms: Optional[int] = None


class FollowUpRequest(BaseModel):
    question: str


class StatusRequest(BaseModel):
    elapsed_minutes: float = 0


class LLMConfigRequest(BaseModel):
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    provider: str = "openai"
    temperature: float = 0.7
    max_tokens: int = 2048


class LLMToggleRequest(BaseModel):
    enabled: bool = True


class ProfileRequest(BaseModel):
    position: dict
    requirements: dict


class CandidateRequest(BaseModel):
    name: str
    experiences: list
