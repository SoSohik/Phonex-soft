import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
DATA_DIR = BASE_DIR / "data"
SETTINGS_JSON = DATA_DIR / "settings.json"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

DEFAULT_API_ID = 36556791
DEFAULT_API_HASH = "c3ca14421b7b63a1ae1bb40bb5fb194d"


@dataclass
class AppConfig:
    api_id: int = DEFAULT_API_ID
    api_hash: str = DEFAULT_API_HASH
    target_bot: str = "@phonegetcardsbot"
    command: str = "/tcard"
    language: str = "en"
    chat_limit: int = 30
    safety_jitter_seconds: int = 5
    default_interval_seconds: int = 3 * 3600
    auto_start: bool = False

    @classmethod
    def load(cls) -> "AppConfig":
        config = cls()
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        env_api_id = os.getenv("TELEGRAM_API_ID", "").strip()
        if env_api_id.isdigit():
            config.api_id = int(env_api_id)
        config.api_hash = os.getenv("TELEGRAM_API_HASH", "").strip() or config.api_hash
        config.target_bot = os.getenv("TARGET_BOT_USERNAME", "").strip() or config.target_bot
        config.command = os.getenv("COMMAND", "").strip() or config.command

        try:
            h = float(os.getenv("DEFAULT_INTERVAL_HOURS", "3"))
            config.default_interval_seconds = int(h * 3600)
        except ValueError:
            pass

        if SETTINGS_JSON.exists():
            try:
                with open(SETTINGS_JSON, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "api_id" in data and data["api_id"]:
                        config.api_id = int(data["api_id"])
                    if "api_hash" in data:
                        config.api_hash = str(data["api_hash"])
                    if "target_bot" in data:
                        config.target_bot = str(data["target_bot"])
                    if "command" in data:
                        config.command = str(data["command"])
                    if "language" in data:
                        config.language = str(data["language"])
                    if "chat_limit" in data:
                        config.chat_limit = int(data["chat_limit"])
                    if "safety_jitter_seconds" in data:
                        config.safety_jitter_seconds = int(data["safety_jitter_seconds"])
                    if "auto_start" in data:
                        config.auto_start = bool(data["auto_start"])
            except Exception:
                pass

        return config

    def save(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(SETTINGS_JSON, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=2, ensure_ascii=False)
        except Exception:
            pass
