"""语音交互系统抽象层"""
import os
import uuid
from datetime import datetime


class SpeechService:
    def __init__(self, records_dir: str = None):
        import config
        self._records_dir = records_dir or os.path.join(config.INTERVIEWS_DIR, "records")
        os.makedirs(self._records_dir, exist_ok=True)

    def save_audio_segment(self, audio_data: bytes, format: str = "webm") -> dict:
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
        return "【ASR 转写结果 - Demo模式】"

    def text_to_speech(self, text: str, voice: str = "zh-CN") -> bytes:
        return b""


class WebSpeechConfig:
    @staticmethod
    def get_config(language: str = "zh-CN") -> dict:
        return {
            "asr": {"language": language, "continuous": True, "interim_results": True, "max_alternatives": 1},
            "tts": {"language": language, "rate": 1.0, "pitch": 1.0, "volume": 1.0,
                    "voice_name": "Microsoft YaHei - Chinese (Simplified)"},
        }
