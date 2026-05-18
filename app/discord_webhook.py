from __future__ import annotations

import requests

from app.scoring import BuzzItem


def build_embed(item: BuzzItem) -> dict:
    """Create one Discord Embed payload for a buzz item."""
    keyword_text = ", ".join(item.related_keywords) if item.related_keywords else "未検出"
    breakdown_text = "\n".join(
        f"- {name}: {value}" for name, value in item.breakdown().items()
    )

    anime_meta = []
    if item.anilist_status:
        anime_meta.append(f"放送状態: {item.anilist_status}")
    if item.season_year:
        anime_meta.append(f"放送年: {item.season_year}")
    if item.season:
        anime_meta.append(f"シーズン: {item.season}")
    if item.format:
        anime_meta.append(f"形式: {item.format}")

    anime_meta_text = "\n".join(anime_meta)
    if anime_meta_text:
        anime_meta_text = f"{anime_meta_text}\n"

    current_related = (
        "不明"
        if item.ai_is_current_season_related is None
        else str(item.ai_is_current_season_related)
    )

    return {
        "title": item.title[:256],
        "url": item.url,
        "description": (
            f"関連キーワード: {keyword_text}\n"
            f"{anime_meta_text}"
            f"話題度スコア: {item.trend_score:.2f}\n\n"
            f"AI要約: {item.ai_summary}\n"
            f"話題の理由: {item.ai_buzz_reason}\n"
            f"カテゴリ: {item.ai_category}\n"
            f"今期関連: {current_related}\n\n"
            f"内訳:\n{breakdown_text}"
        )[:4096],
        "color": 0xFF6B8A,
        "footer": {"text": f"Source: {item.source}"},
    }


def post_to_discord(
    webhook_url: str,
    items: list[BuzzItem],
    excluded_count: int = 0,
) -> None:
    """Post top buzz items to Discord using a Webhook."""
    if not webhook_url:
        raise ValueError("DISCORD_WEBHOOK_URL is not set. Please add it to .env.")

    if not items:
        print("No new buzz items to post.")
        return

    payload = {
        "username": "Anime Buzz Watcher",
        "content": "今期・最近話題のアニメ関連コンテンツです。",
        "embeds": [build_embed(item) for item in items],
    }

    response = requests.post(webhook_url, json=payload, timeout=20)
    response.raise_for_status()
