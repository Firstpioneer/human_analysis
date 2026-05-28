"""
阿里云智能语音交互服务 (TTS 语音合成 + ASR 语音识别)

使用阿里云 NLS (Natural Language Processing) REST API：
  - TTS: POST https://nls-gateway-{region}.aliyuncs.com/stream/v1/tts
  - ASR: POST https://nls-gateway-{region}.aliyuncs.com/stream/v1/asr

认证方式：
  通过阿里云 SDK (aliyun-python-sdk-core) 调用 CreateToken 获取临时 Token

前置条件：
  1. 开通阿里云智能语音交互服务 https://nls.console.aliyun.com
  2. 创建项目获取 AppKey
  3. 创建 RAM 用户获取 AccessKeyId 和 AccessKeySecret
  4. 将凭证填入 .env.json 或环境变量
"""
import os
import json
import time
import uuid
import logging
from datetime import datetime
from typing import Optional

import requests
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  阿里云 NLS Token 管理
# ──────────────────────────────────────────────

class AliyunTokenManager:
    """管理阿里云 NLS 服务的临时 Token（使用 SDK 认证）"""

    def __init__(self, access_key_id: str, access_key_secret: str):
        self._ak_id = access_key_id
        self._ak_secret = access_key_secret
        self._token: Optional[str] = None
        self._expire_time: int = 0
        self._client = AcsClient(access_key_id, access_key_secret, "cn-shanghai")

    def get_token(self) -> str:
        """获取有效的 Token（自动刷新）"""
        if self._token and time.time() < self._expire_time - 60:
            return self._token
        return self._refresh_token()

    def _refresh_token(self) -> str:
        """通过阿里云 SDK 获取新的 Token"""
        try:
            req = CommonRequest()
            req.set_domain("nls-meta.cn-shanghai.aliyuncs.com")
            req.set_version("2019-02-28")
            req.set_action_name("CreateToken")
            req.set_method("POST")

            resp = self._client.do_action_with_exception(req)
            data = json.loads(resp)

            token_info = data.get("Token", {})
            self._token = token_info.get("Id", "")
            expire_ts = token_info.get("ExpireTime", 0)
            self._expire_time = expire_ts if expire_ts else 0

            logger.info("阿里云 NLS Token 刷新成功")
            return self._token

        except Exception as e:
            logger.error(f"获取 Token 失败: {e}")
            raise RuntimeError(f"获取阿里云 NLS Token 失败: {e}")
        except requests.RequestException as e:
            logger.error(f"获取 Token 网络错误: {e}")
            raise RuntimeError(f"获取阿里云 Token 网络错误: {e}")


# ──────────────────────────────────────────────
#  阿里云 NLS 语音服务
# ──────────────────────────────────────────────

class AliyunNLSService:
    """
    阿里云智能语音交互服务

    提供 TTS（文字转语音）和 ASR（语音转文字）功能。
    """

    AVAILABLE_VOICES = {
        "xiaoyun": "标准女声（推荐）",
        "xiaogang": "标准男声",
        "ruoxi": "温柔女声",
        "siqi": "活泼女声",
        "sijia": "甜美女声",
        "zhiyu": "情感女声",
        "zeqi": "阳光男声",
        "shanshan": "温柔女声",
    }

    def __init__(
        self,
        access_key_id: str = "",
        access_key_secret: str = "",
        app_key: str = "",
        region: str = "cn-shanghai",
        records_dir: str = None,
    ):
        self._ak_id = access_key_id or os.getenv("ALIYUN_NLS_AK_ID", "")
        self._ak_secret = access_key_secret or os.getenv("ALIYUN_NLS_AK_SECRET", "")
        self._app_key = app_key or os.getenv("ALIYUN_NLS_APP_KEY", "")
        self._region = region or os.getenv("ALIYUN_NLS_REGION", "cn-shanghai")

        self._tts_url = f"https://nls-gateway-{self._region}.aliyuncs.com/stream/v1/tts"
        self._asr_url = f"https://nls-gateway-{self._region}.aliyuncs.com/stream/v1/asr"

        self._token_mgr = AliyunTokenManager(self._ak_id, self._ak_secret)

        import config
        self._records_dir = records_dir or os.path.join(config.INTERVIEWS_DIR, "records")
        os.makedirs(self._records_dir, exist_ok=True)

    @property
    def is_configured(self) -> bool:
        """检查是否配置了有效的阿里云 NLS 凭证"""
        return bool(
            self._ak_id and self._ak_secret and self._app_key
            and not self._ak_id.startswith("你的")
            and not self._ak_secret.startswith("你的")
            and not self._app_key.startswith("你的")
        )

    @property
    def configured_voices(self) -> dict:
        return dict(self.AVAILABLE_VOICES)

    # ── TTS: 文字转语音 ──

    def text_to_speech(
        self,
        text: str,
        voice: str = "xiaoyun",
        format: str = "wav",
        sample_rate: int = 16000,
        volume: int = 50,
        speech_rate: int = 0,
        pitch_rate: int = 0,
    ) -> bytes:
        """
        文字转语音

        参数:
            text: 要合成的文本（最长 500 字）
            voice: 发音人
            format: 音频格式（wav/mp3/pcm）
            sample_rate: 采样率（8000/16000/24000/48000）
            volume: 音量（0-100）
            speech_rate: 语速（-500 ~ 500）
            pitch_rate: 音调（-500 ~ 500）

        返回:
            bytes: 音频二进制数据
        """
        if not self.is_configured:
            logger.warning("阿里云 NLS 未配置，返回空音频")
            return b""

        if not text or not text.strip():
            return b""

        if len(text) > 500:
            text = text[:500]

        token = self._token_mgr.get_token()

        headers = {
            "Content-Type": "application/json",
            "X-NLS-Token": token,
        }

        payload = {
            "appkey": self._app_key,
            "text": text,
            "format": format,
            "sample_rate": sample_rate,
            "voice": voice,
            "volume": volume,
            "speech_rate": speech_rate,
            "pitch_rate": pitch_rate,
            "enable_subtitle": False,
        }

        try:
            resp = requests.post(self._tts_url, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200:
                logger.info(f"TTS 合成成功: text_len={len(text)}, audio_size={len(resp.content)} bytes")
                return resp.content
            else:
                error_msg = f"TTS 合成失败: HTTP {resp.status_code}"
                try:
                    err = resp.json()
                    error_msg += f" - {err.get('message', resp.text[:200])}"
                except Exception:
                    error_msg += f" - {resp.text[:200]}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
        except requests.RequestException as e:
            logger.error(f"TTS 网络错误: {e}")
            raise RuntimeError(f"TTS 网络请求失败: {e}")

    def text_to_speech_file(self, text: str, voice: str = "xiaoyun", format: str = "wav") -> Optional[str]:
        """TTS 合成并保存到文件"""
        audio = self.text_to_speech(text, voice=voice, format=format)
        if not audio:
            return None
        filename = f"tts_{uuid.uuid4().hex[:8]}.{format}"
        filepath = os.path.join(self._records_dir, filename)
        with open(filepath, "wb") as f:
            f.write(audio)
        return filepath

    # ── ASR: 语音转文字 ──

    def transcribe_speech(self, audio_file_path: str, format: str = "wav", sample_rate: int = 16000) -> str:
        """
        语音转文字

        参数:
            audio_file_path: 音频文件路径
            format: 音频格式（wav/mp3/pcm/m4a/ogg）
            sample_rate: 采样率

        返回:
            str: 识别出的文字
        """
        if not self.is_configured:
            return "【ASR 服务未配置】"

        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_file_path}")

        token = self._token_mgr.get_token()

        with open(audio_file_path, "rb") as f:
            audio_data = f.read()

        headers = {
            "Content-Type": f"audio/{format}",
            "X-NLS-Token": token,
        }

        params = {
            "appkey": self._app_key,
            "format": format,
            "sample_rate": sample_rate,
            "enable_punctuation_prediction": True,
            "enable_inverse_text_normalization": True,
            "enable_voice_detection": True,
        }

        try:
            resp = requests.post(self._asr_url, params=params, headers=headers, data=audio_data, timeout=60)
            if resp.status_code == 200:
                result = resp.json()
                if result.get("status") == 20000000:
                    text = result.get("result", "")
                    logger.info(f"ASR 识别成功: text_len={len(text)}")
                    return text
                else:
                    raise RuntimeError(f"ASR 识别失败: {result.get('status')} - {result.get('message', '未知错误')}")
            else:
                raise RuntimeError(f"ASR 请求失败: HTTP {resp.status_code} {resp.text[:200]}")
        except requests.RequestException as e:
            logger.error(f"ASR 网络错误: {e}")
            raise RuntimeError(f"ASR 网络请求失败: {e}")

    def transcribe_speech_bytes(self, audio_data: bytes, format: str = "wav", sample_rate: int = 16000) -> str:
        """直接传入音频 bytes 进行语音识别"""
        if not self.is_configured:
            return "【ASR 服务未配置】"

        token = self._token_mgr.get_token()
        headers = {"Content-Type": f"audio/{format}", "X-NLS-Token": token}
        params = {
            "appkey": self._app_key, "format": format, "sample_rate": sample_rate,
            "enable_punctuation_prediction": True, "enable_inverse_text_normalization": True,
            "enable_voice_detection": True,
        }
        try:
            resp = requests.post(self._asr_url, params=params, headers=headers, data=audio_data, timeout=60)
            if resp.status_code == 200:
                result = resp.json()
                if result.get("status") == 20000000:
                    return result.get("result", "")
            return ""
        except Exception as e:
            logger.error(f"ASR bytes 识别错误: {e}")
            return ""

    def save_audio_segment(self, audio_data: bytes, format: str = "wav") -> dict:
        """保存音频数据段到文件"""
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


class WebSpeechConfig:
    """前端 Web Speech API 配置"""

    @staticmethod
    def get_config(language: str = "zh-CN") -> dict:
        return {
            "asr": {
                "language": language, "continuous": True,
                "interim_results": True, "max_alternatives": 1,
            },
            "tts": {
                "language": language, "rate": 1.0, "pitch": 1.0,
                "volume": 1.0,
                "voice_name": "Microsoft YaHei - Chinese (Simplified)",
            },
        }


def create_speech_service() -> AliyunNLSService:
    """从环境变量 / .env.json 创建语音服务实例"""
    import config as app_config

    nls_config = {}
    env_file = os.path.join(app_config.BASE_DIR, ".env.json")
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                env_data = json.load(f)
            nls_config = env_data.get("aliyun_nls", {})
        except Exception:
            pass

    return AliyunNLSService(
        access_key_id=nls_config.get("access_key_id", ""),
        access_key_secret=nls_config.get("access_key_secret", ""),
        app_key=nls_config.get("app_key", ""),
        region=nls_config.get("region", "cn-shanghai"),
    )
