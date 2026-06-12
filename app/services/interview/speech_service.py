"""
面试语音服务（TTS + ASR）

- TTS: 支持 MIMO v2.5-tts 作为主提供方，阿里云 NLS 作为回退
- ASR: 继续使用阿里云 NLS
"""
import base64
import binascii
import json
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Any, Optional

import requests

try:
    from aliyunsdkcore.client import AcsClient
    from aliyunsdkcore.request import CommonRequest
except ImportError:
    AcsClient = None
    CommonRequest = None

logger = logging.getLogger(__name__)

ALIYUN_SDK_INSTALL_HINT = "请先安装 aliyun-python-sdk-core：pip install aliyun-python-sdk-core"


def _load_local_json_config() -> dict:
    import config as app_config

    env_file = os.path.join(app_config.BASE_DIR, ".env.json")
    if not os.path.exists(env_file):
        return {}
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _get_interview_tts_config(env_data: dict) -> dict:
    return env_data.get("interview_tts", {}) if isinstance(env_data, dict) else {}


class AliyunTokenManager:
    """管理阿里云 NLS 服务的临时 Token（使用 SDK 认证）"""

    def __init__(self, access_key_id: str, access_key_secret: str):
        if AcsClient is None:
            raise RuntimeError(f"阿里云 SDK 未安装，无法获取 NLS Token。{ALIYUN_SDK_INSTALL_HINT}")

        self._ak_id = access_key_id
        self._ak_secret = access_key_secret
        self._token: Optional[str] = None
        self._expire_time: int = 0
        self._client = AcsClient(access_key_id, access_key_secret, "cn-shanghai")

    def get_token(self) -> str:
        if self._token and time.time() < self._expire_time - 60:
            return self._token
        return self._refresh_token()

    def _refresh_token(self) -> str:
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
            self._expire_time = token_info.get("ExpireTime", 0) or 0
            logger.info("阿里云 NLS Token 刷新成功")
            return self._token
        except Exception as e:
            logger.error(f"获取 Token 失败: {e}")
            raise RuntimeError(f"获取阿里云 NLS Token 失败: {e}")


class AliyunNLSService:
    """阿里云智能语音交互服务，提供 TTS 与 ASR。"""

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

        self._token_mgr = None
        if self._ak_id and self._ak_secret and AcsClient is not None:
            self._token_mgr = AliyunTokenManager(self._ak_id, self._ak_secret)
        elif self._ak_id and self._ak_secret:
            logger.warning("阿里云 SDK 未安装，TTS/ASR 功能不可用。%s", ALIYUN_SDK_INSTALL_HINT)

        import config
        self._records_dir = records_dir or os.path.join(config.INTERVIEWS_DIR, "records")
        os.makedirs(self._records_dir, exist_ok=True)

    @property
    def is_configured(self) -> bool:
        return bool(
            AcsClient is not None
            and self._token_mgr is not None
            and self._ak_id and self._ak_secret and self._app_key
            and not self._ak_id.startswith("你的")
            and not self._ak_secret.startswith("你的")
            and not self._app_key.startswith("你的")
        )

    @property
    def configured_voices(self) -> dict:
        return dict(self.AVAILABLE_VOICES)

    def normalize_tts_format(self, format: str) -> str:
        return format if format in {"wav", "mp3", "pcm"} else "wav"

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
        if not self.is_configured:
            logger.warning("阿里云 NLS 未配置，返回空音频")
            return b""
        if not text or not text.strip():
            return b""

        if len(text) > 500:
            text = text[:500]

        token = self._token_mgr.get_token()
        headers = {"Content-Type": "application/json", "X-NLS-Token": token}
        payload = {
            "appkey": self._app_key,
            "text": text,
            "format": self.normalize_tts_format(format),
            "sample_rate": sample_rate,
            "voice": voice if voice in self.AVAILABLE_VOICES else "xiaoyun",
            "volume": volume,
            "speech_rate": speech_rate,
            "pitch_rate": pitch_rate,
            "enable_subtitle": False,
        }

        try:
            resp = requests.post(self._tts_url, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200:
                logger.info("Aliyun TTS 合成成功: text_len=%s audio_size=%s", len(text), len(resp.content))
                return resp.content
            error_msg = f"Aliyun TTS 合成失败: HTTP {resp.status_code}"
            try:
                err = resp.json()
                error_msg += f" - {err.get('message', resp.text[:200])}"
            except Exception:
                error_msg += f" - {resp.text[:200]}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except requests.RequestException as e:
            logger.error("Aliyun TTS 网络错误: %s", e)
            raise RuntimeError(f"Aliyun TTS 网络请求失败: {e}")

    def text_to_speech_file(self, text: str, voice: str = "xiaoyun", format: str = "wav") -> Optional[str]:
        audio = self.text_to_speech(text, voice=voice, format=format)
        if not audio:
            return None
        filename = f"tts_{uuid.uuid4().hex[:8]}.{format}"
        filepath = os.path.join(self._records_dir, filename)
        with open(filepath, "wb") as f:
            f.write(audio)
        return filepath

    def transcribe_speech(self, audio_file_path: str, format: str = "wav", sample_rate: int = 16000) -> str:
        if not self.is_configured:
            return "【ASR 服务未配置】"
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_file_path}")

        token = self._token_mgr.get_token()
        with open(audio_file_path, "rb") as f:
            audio_data = f.read()

        headers = {"Content-Type": f"audio/{format}", "X-NLS-Token": token}
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
                    logger.info("ASR 识别成功: text_len=%s", len(text))
                    return text
                raise RuntimeError(f"ASR 识别失败: {result.get('status')} - {result.get('message', '未知错误')}")
            raise RuntimeError(f"ASR 请求失败: HTTP {resp.status_code} {resp.text[:200]}")
        except requests.RequestException as e:
            logger.error("ASR 网络错误: %s", e)
            raise RuntimeError(f"ASR 网络请求失败: {e}")

    def transcribe_speech_bytes(self, audio_data: bytes, format: str = "wav", sample_rate: int = 16000) -> str:
        if not self.is_configured:
            return "【ASR 服务未配置】"

        token = self._token_mgr.get_token()
        headers = {"Content-Type": f"audio/{format}", "X-NLS-Token": token}
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
                    return result.get("result", "")
            return ""
        except Exception as e:
            logger.error("ASR bytes 识别错误: %s", e)
            return ""

    def save_audio_segment(self, audio_data: bytes, format: str = "wav") -> dict:
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


class MimoTTSProvider:
    """MIMO v2.5-tts 语音提供方。"""

    DEFAULT_STYLE_PROMPT = (
        "Speak like a professional interviewer in a real online interview. "
        "Calm, clear, natural, slightly warm, not exaggerated, with short natural pauses between clauses."
    )

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://token-plan-cn.xiaomimimo.com/v1",
        model: str = "mimo-v2.5-tts",
        voice: str = "mimo_default",
        audio_format: str = "wav",
        timeout: int = 60,
    ):
        self._api_key = api_key or os.getenv("MIMO_TTS_API_KEY", "")
        self._base_url = (base_url or os.getenv("MIMO_TTS_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1")).rstrip("/")
        if self._base_url.endswith("/chat/completions"):
            self._base_url = self._base_url[: -len("/chat/completions")]
        self._model = model or os.getenv("MIMO_TTS_MODEL", "mimo-v2.5-tts")
        self._voice = voice or os.getenv("MIMO_TTS_VOICE", "mimo_default")
        self._audio_format = audio_format or os.getenv("MIMO_TTS_FORMAT", "wav")
        self._timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key and not self._api_key.startswith("你的"))

    @property
    def configured_voices(self) -> dict:
        return {self._voice: "MIMO 默认音色"}

    def normalize_tts_format(self, format: str) -> str:
        return "wav"

    def text_to_speech(
        self,
        text: str,
        voice: str = "",
        format: str = "wav",
        sample_rate: int = 16000,
        volume: int = 50,
        speech_rate: int = 0,
        pitch_rate: int = 0,
    ) -> bytes:
        del sample_rate, volume
        if not self.is_configured:
            return b""
        if not text or not text.strip():
            return b""

        payload = {
            "model": self._model,
            "messages": [
                {"role": "assistant", "content": text[:1000]},
            ],
            "audio": {
                "format": self.normalize_tts_format(format),
                "voice": self._resolve_voice(voice),
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
            "api-key": self._api_key,
            "X-API-Key": self._api_key,
        }
        url = f"{self._base_url}/chat/completions"
        logger.info("MIMO TTS 请求: url=%s api_key=%s****", url, self._api_key[:8] if len(self._api_key) > 8 else "(短key)")

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=self._timeout)
            if resp.status_code != 200:
                raise RuntimeError(f"MIMO TTS 请求失败: HTTP {resp.status_code} {resp.text[:200]}")
            audio_bytes = self._extract_audio_bytes(resp)
            if not audio_bytes:
                logger.error("MIMO TTS 返回内容: content_type=%s body_len=%s body_prefix=%s",
                             resp.headers.get("Content-Type"), len(resp.content), resp.content[:200])
                raise RuntimeError("MIMO TTS 未返回可用音频数据")
            logger.info("MIMO TTS 合成成功: text_len=%s audio_size=%s audio_prefix=%s",
                        len(text), len(audio_bytes), audio_bytes[:20])
            return audio_bytes
        except requests.RequestException as e:
            logger.error("MIMO TTS 网络错误: %s", e)
            raise RuntimeError(f"MIMO TTS 网络请求失败: {e}")

    def _resolve_voice(self, voice: str) -> str:
        if not voice or voice in AliyunNLSService.AVAILABLE_VOICES:
            return self._voice
        return voice

    def _build_style_prompt(self, speech_rate: int, pitch_rate: int) -> str:
        traits = [self.DEFAULT_STYLE_PROMPT]
        if speech_rate > 100:
            traits.append("Speak slightly faster than average.")
        elif speech_rate < -100:
            traits.append("Speak slightly slower than average.")
        if pitch_rate > 100:
            traits.append("Use a slightly brighter tone.")
        elif pitch_rate < -100:
            traits.append("Use a slightly lower, steadier tone.")
        return " ".join(traits)

    def _extract_audio_bytes(self, response: requests.Response) -> bytes:
        content_type = (response.headers.get("Content-Type") or "").lower()
        raw = response.content or b""

        if raw[:4] == b"RIFF" or raw[:4] == b"OggS" or raw[:3] == b"ID3":
            return raw
        if content_type.startswith("audio/") or content_type == "application/octet-stream":
            return raw

        try:
            payload = response.json()
        except ValueError as e:
            raise RuntimeError(f"MIMO TTS 返回格式无法识别: {e}")

        audio_data = self._extract_audio_from_json(payload)
        if audio_data:
            return audio_data

        raise RuntimeError("MIMO TTS 响应中未找到音频字段")

    def _extract_audio_from_json(self, payload: Any) -> bytes:
        """从 OpenAI 兼容响应中提取音频数据。路径: choices[0].message.audio.data"""
        if not isinstance(payload, dict):
            return b""

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            return b""

        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if not isinstance(message, dict):
            return b""

        audio_obj = message.get("audio")
        if not isinstance(audio_obj, dict):
            return b""

        data_str = audio_obj.get("data")
        if isinstance(data_str, str) and data_str.strip():
            decoded = self._decode_base64_audio(data_str)
            if decoded:
                return decoded

        for value in audio_obj.values():
            if isinstance(value, str) and value.strip():
                decoded = self._decode_base64_audio(value)
                if decoded:
                    return decoded

        return b""

    def _decode_base64_audio(self, value: Any) -> bytes:
        if not isinstance(value, str):
            return b""

        candidate = value.strip()
        if candidate.startswith("data:") and "," in candidate:
            candidate = candidate.split(",", 1)[1]
        if len(candidate) < 1000:
            return b""
        try:
            return base64.b64decode(candidate, validate=True)
        except (binascii.Error, ValueError):
            return b""


class InterviewSpeechService:
    """统一语音服务：MIMO TTS + Aliyun ASR。"""

    def __init__(self, primary_provider: str, fallback_provider: str, providers: dict[str, Any], asr_service: AliyunNLSService):
        self._primary_provider = primary_provider
        self._fallback_provider = fallback_provider
        self._providers = providers
        self._asr_service = asr_service

    @property
    def tts_configured(self) -> bool:
        return any(provider and provider.is_configured for provider in self._providers.values())

    @property
    def asr_configured(self) -> bool:
        return self._asr_service.is_configured

    @property
    def is_configured(self) -> bool:
        return self.tts_configured

    @property
    def configured_voices(self) -> dict:
        provider = self._resolve_tts_provider()
        if provider and provider.is_configured:
            return provider.configured_voices
        return {}

    def resolve_tts_format(self, requested_format: str) -> str:
        provider = self._resolve_tts_provider()
        if provider and hasattr(provider, "normalize_tts_format"):
            return provider.normalize_tts_format(requested_format)
        return requested_format or "wav"

    def text_to_speech(self, **kwargs) -> bytes:
        errors = []
        for name, provider in self._tts_chain():
            try:
                normalized_kwargs = dict(kwargs)
                normalized_kwargs["format"] = provider.normalize_tts_format(normalized_kwargs.get("format", "wav"))
                audio = provider.text_to_speech(**normalized_kwargs)
                if audio:
                    if name != self._primary_provider:
                        logger.warning("TTS 已回退到提供方: %s", name)
                    return audio
            except RuntimeError as e:
                logger.warning("TTS 提供方 %s 调用失败: %s", name, e)
                errors.append(f"{name}: {e}")
        raise RuntimeError("所有语音服务都不可用：" + " | ".join(errors or ["未配置 TTS 提供方"]))

    def transcribe_speech_bytes(self, *args, **kwargs) -> str:
        return self._asr_service.transcribe_speech_bytes(*args, **kwargs)

    def _resolve_tts_provider(self):
        for _, provider in self._tts_chain():
            if provider and provider.is_configured:
                return provider
        return None

    def _tts_chain(self):
        seen = set()
        for name in (self._primary_provider, self._fallback_provider):
            if not name or name in seen:
                continue
            seen.add(name)
            provider = self._providers.get(name)
            if provider and provider.is_configured:
                yield name, provider


class WebSpeechConfig:
    """前端 Web Speech API 配置"""

    @staticmethod
    def get_config(language: str = "zh-CN") -> dict:
        return {
            "asr": {
                "language": language,
                "continuous": True,
                "interim_results": True,
                "max_alternatives": 1,
            },
            "tts": {
                "language": language,
                "rate": 1.0,
                "pitch": 1.0,
                "volume": 1.0,
                "voice_name": "Microsoft YaHei - Chinese (Simplified)",
            },
        }


def create_speech_service() -> InterviewSpeechService:
    """从环境变量 / .env.json 创建语音服务实例。"""
    env_data = _load_local_json_config()
    nls_config = env_data.get("aliyun_nls", {}) if isinstance(env_data, dict) else {}
    tts_config = _get_interview_tts_config(env_data)

    aliyun_service = AliyunNLSService(
        access_key_id=nls_config.get("access_key_id", ""),
        access_key_secret=nls_config.get("access_key_secret", ""),
        app_key=nls_config.get("app_key", ""),
        region=nls_config.get("region", "cn-shanghai"),
    )

    mimo_config = tts_config.get("mimo", {}) if isinstance(tts_config, dict) else {}
    mimo_provider = MimoTTSProvider(
        api_key=mimo_config.get("api_key", ""),
        base_url=mimo_config.get("base_url", "https://token-plan-cn.xiaomimimo.com/v1"),
        model=mimo_config.get("model", "mimo-v2.5-tts"),
        voice=mimo_config.get("voice", "mimo_default"),
        audio_format=mimo_config.get("format", "wav"),
    )

    primary_provider = tts_config.get("provider") or os.getenv("INTERVIEW_TTS_PROVIDER", "mimo")
    fallback_provider = tts_config.get("fallback_provider") or os.getenv("INTERVIEW_TTS_FALLBACK_PROVIDER", "")

    providers = {
        "mimo": mimo_provider,
    }

    return InterviewSpeechService(
        primary_provider=primary_provider,
        fallback_provider=fallback_provider,
        providers=providers,
        asr_service=aliyun_service,
    )
