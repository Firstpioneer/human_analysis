"""面试模块服务层"""
from .speech_service import AliyunNLSService, AliyunTokenManager, WebSpeechConfig, create_speech_service

__all__ = ["AliyunNLSService", "AliyunTokenManager", "WebSpeechConfig", "create_speech_service"]
