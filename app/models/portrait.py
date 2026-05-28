"""画像模块数据模型"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class Message(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ChatRequest(BaseModel):
    message: str
    api_key: str
    conversation_id: Optional[str] = None
    messages: list[Message] = Field(default_factory=list)
    generate_profile: bool = False


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str
    messages: list[Message]
    profile_draft: Optional[dict] = None
    phase: str = "clarify"


class GenerateProfileRequest(BaseModel):
    api_key: str
    messages: list[Message]
    conversation_id: Optional[str] = None


class GenerateProfileResponse(BaseModel):
    profile: dict
    conversation_id: str


class SaveProfileRequest(BaseModel):
    profile: dict
    conversation_id: Optional[str] = None
    messages: list[Message] = Field(default_factory=list)


class SignalDimension(BaseModel):
    name: str
    description: str = ""
    evaluation_criteria: str = ""
    weight: str = "参考"
    example_questions: list[str] = Field(default_factory=list)


class SignalCategory(BaseModel):
    category: str
    dimensions: list[SignalDimension] = Field(default_factory=list)


class CoreRole(BaseModel):
    role_name: str
    description: str = ""
    key_responsibilities: list[str] = Field(default_factory=list)


class CompanyContext(BaseModel):
    why_hire: str = ""
    team_description: str = ""
    business_context: str = ""


class JobProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    status: str = "draft"
    job_title: str = ""
    company_context: CompanyContext = Field(default_factory=CompanyContext)
    core_roles: list[CoreRole] = Field(default_factory=list)
    signal_dimensions: list[SignalCategory] = Field(default_factory=list)
    must_have: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    anti_profile: list[str] = Field(default_factory=list)
    general_questions: list[str] = Field(default_factory=list)
    conversation_summary: str = ""
    jd原文: str = ""
