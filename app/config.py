from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    discord_webhook_url: str
    x_bearer_token: str | None
    openai_api_key: str | None
    openai_model: str
    keywords_path: Path
    excluded_keywords_path: Path
    filter_rules_path: Path
    posted_items_path: Path
    check_interval_minutes: int
    top_n: int = 5


def parse_check_interval_minutes(raw_value: str | None) -> int:
    """Parse CHECK_INTERVAL_MINUTES with a safe default."""
    if not raw_value:
        return 60

    try:
        interval = int(raw_value)
    except ValueError:
        print(
            "Warning: CHECK_INTERVAL_MINUTES is invalid. "
            "Falling back to 60 minutes."
        )
        return 60

    if interval <= 0:
        print(
            "Warning: CHECK_INTERVAL_MINUTES must be greater than 0. "
            "Falling back to 60 minutes."
        )
        return 60

    return interval


def load_settings() -> Settings:
    """Load environment variables and file paths used by the app."""
    load_dotenv(BASE_DIR / ".env")

    return Settings(
        discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL", "").strip(),
        x_bearer_token=os.getenv("X_BEARER_TOKEN", "").strip() or None,
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip() or None,
        openai_model=os.getenv("OPENAI_MODEL", "").strip() or "gpt-5.5",
        keywords_path=BASE_DIR / "config" / "trend_keywords.json",
        excluded_keywords_path=BASE_DIR / "config" / "excluded_keywords.json",
        filter_rules_path=BASE_DIR / "config" / "filter_rules.json",
        posted_items_path=BASE_DIR / "data" / "posted_items.json",
        check_interval_minutes=parse_check_interval_minutes(
            os.getenv("CHECK_INTERVAL_MINUTES")
        ),
    )


def load_keywords(path: Path) -> list[str]:
    """Read anime-related keywords from a JSON file."""
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        return []

    if isinstance(data, dict):
        keywords = data.get("keywords", [])
    else:
        keywords = data

    return [str(keyword).strip() for keyword in keywords if str(keyword).strip()]


def load_filter_rules(path: Path) -> dict:
    """Read season and long-running title filter settings."""
    default_rules = {
        "exclude_long_running": True,
        "max_episode_count": 100,
        "max_old_season_years": 2,
        "prefer_releasing": True,
        "prefer_current_season": True,
    }

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return default_rules

    if not isinstance(data, dict):
        return default_rules

    return {**default_rules, **data}
