"""
语音交互系统抽象层 (ASR + TTS)
后端提供接口，前端使用浏览器 Web Speech API 实现实时语音交互
"""

import json
import os
import uuid
from datetime import datetime


class SpeechService:
    """语音服务抽象层"""

    def __init__(self, records_dir: str = None):
        self._records_dir = records_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data", "records"
        )
        os.makedirs(self._records_dir, exist_ok=True)

    def save_audio_segment(self, audio_data: bytes, format: str = "webm") -> dict:
        """
        保存音频片段

        Args:
            audio_data: 音频二进制数据
            format: 音频格式

        Returns:
            音频记录信息
        """
        segment_id = f"audio_{uuid.uuid4().hex[:8]}"
        filename = f"{segment_id}.{format}"
        filepath = os.path.join(self._records_dir, filename)

        with open(filepath, "wb") as f:
            f.write(audio_data)

        return {
            "segment_id": segment_id,
            "file_path": filepath,
            "timestamp": datetime.now().isoformat(),
            "format": format,
        }

    def transcribe_speech(self, audio_file_path: str) -> str:
        """
        ASR 语音转文字
        实际生产环境会调用第三方 ASR API（如阿里云、讯飞、Azure等）
        此处 demo 模式返回模拟结果

        Args:
            audio_file_path: 音频文件路径

        Returns:
            转写文本
        """
        # Demo: 模拟 ASR 结果
        # 实际使用时可替换为真实 ASR 服务调用
        return "【ASR 转写结果 - Demo模式】"

    def text_to_speech(self, text: str, voice: str = "zh-CN") -> bytes:
        """
        TTS 文字转语音
        实际生产环境会调用第三方 TTS API
        此处仅返回接口定义

        Args:
            text: 待合成的文本
            voice: 语音角色

        Returns:
            音频二进制数据
        """
        # Demo: 返回空数据，实际由前端 Web Speech API 实现
        # 生产环境可替换为 Azure TTS / 讯飞 TTS 等
        return b""


class WebSpeechConfig:
    """前端 Web Speech API 配置"""

    @staticmethod
    def get_config(language: str = "zh-CN") -> dict:
        """获取语音配置"""
        return {
            "asr": {
                "language": language,
                "continuous": True,
                "interim_results": True,
                "max_alternatives": 1,
            },
            "tts": {
                "language": language,
                "rate": 1.0,  # 语速 0.1 ~ 10
                "pitch": 1.0,  # 音调 0 ~ 2
                "volume": 1.0,  # 音量 0 ~ 1
                "voice_name": "Microsoft YaHei - Chinese (Simplified)",
            },
        }


# 便捷函数
def create_speech_service():
    return SpeechService()
