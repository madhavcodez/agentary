from pydantic_settings import BaseSettings


class VoiceSettings(BaseSettings):
    gemini_api_key: str = ""
    voice_model: str = "gemini-2.5-flash-native-audio-preview"
    voice_name: str = "Aoede"
    webrtc_port: int = 7860

    class Config:
        env_prefix = "VOICE_"


voice_settings = VoiceSettings()
