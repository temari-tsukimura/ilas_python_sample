from __future__ import annotations

import json
import re
from typing import Any

from app.scoring import BuzzItem


SUMMARY_SCHEMA = {
    "type": "json_schema",
    "name": "anime_buzz_summary",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "summary": {"type": "string"},
            "buzz_reason": {"type": "string"},
            "is_current_season_related": {"type": "boolean"},
            "category": {
                "type": "string",
                "enum": [
                    "今期アニメ",
                    "劇場版",
                    "アニメ化ニュース",
                    "声優・イベント",
                    "その他",
                ],
            },
        },
        "required": [
            "summary",
            "buzz_reason",
            "is_current_season_related",
            "category",
        ],
    },
}


def summarize_items_with_ai(
    items: list[BuzzItem],
    api_key: str | None,
    model: str,
    disabled: bool = False,
) -> None:
    """Add optional OpenAI-generated summaries to each item in-place."""
    if disabled:
        print("AI summarization disabled by --no-ai.")
        return

    if not api_key:
        print("OPENAI_API_KEY is not set. Skipping AI summarization.")
        return

    try:
        from openai import OpenAI
    except ImportError:
        print("openai package is not installed. Skipping AI summarization.")
        return

    client = OpenAI(api_key=api_key)
    for item in items:
        try:
            ai_result = summarize_item(client, model, item)
        except Exception as error:
            print(
                f"AI summarization failed for '{item.title}': "
                f"{safe_error_message(error)}"
            )
            continue

        item.ai_summary = ai_result.get("summary", "AI要約なし")
        item.ai_buzz_reason = ai_result.get("buzz_reason", "AI要約なし")
        item.ai_is_current_season_related = ai_result.get(
            "is_current_season_related"
        )
        item.ai_category = ai_result.get("category", "AI要約なし")


def summarize_item(client: Any, model: str, item: BuzzItem) -> dict:
    """Ask OpenAI for a short Japanese JSON summary for one buzz item."""
    prompt_data = {
        "title": item.title,
        "source": item.source,
        "url": item.url,
        "related_keywords": item.related_keywords,
        "score_breakdown": item.breakdown(),
        "source_excerpt": item.source_excerpt,
        "anilist_status": item.anilist_status,
        "season_year": item.season_year,
        "season": item.season,
        "format": item.format,
        "episodes": item.episodes,
    }

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "あなたはアニメニュースを短く整理するアシスタントです。"
                    "必ず日本語で、指定されたJSON Schemaに従って出力してください。"
                    "誇張せず、入力情報から分かる範囲だけで判断してください。"
                ),
            },
            {
                "role": "user",
                "content": (
                    "次のアニメ関連情報を要約してください。"
                    "summaryは1〜2文、buzz_reasonは1文にしてください。\n"
                    f"{json.dumps(prompt_data, ensure_ascii=False)}"
                ),
            },
        ],
        text={"format": SUMMARY_SCHEMA},
    )

    return json.loads(response.output_text)


def safe_error_message(error: Exception) -> str:
    """Return an error message without exposing API keys in logs."""
    status_code = getattr(error, "status_code", None)
    error_text = str(error)

    if status_code == 401 or "invalid_api_key" in error_text:
        return "OpenAI API key is invalid or not active. Please check OPENAI_API_KEY."

    sanitized = re.sub(r"sk-[A-Za-z0-9_\-]+", "sk-***", error_text)
    return sanitized[:300]
