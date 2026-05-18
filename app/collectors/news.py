from __future__ import annotations

from urllib.parse import quote_plus

import feedparser
import requests

from app.scoring import BuzzItem, find_related_keywords


def fetch_google_news(keywords: list[str], limit_per_keyword: int = 3) -> list[BuzzItem]:
    """Fetch anime-related news from Google News RSS."""
    items: list[BuzzItem] = []

    for keyword in keywords:
        query = quote_plus(f"{keyword} anime OR アニメ")
        feed_url = (
            "https://news.google.com/rss/search?"
            f"q={query}&hl=ja&gl=JP&ceid=JP:ja"
        )

        try:
            response = requests.get(feed_url, timeout=8)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
        except Exception as error:
            print(f"Google News collector failed for {keyword}: {error}")
            continue

        if getattr(feed, "bozo", False):
            print(f"Google News RSS parse warning for {keyword}: {feed.bozo_exception}")

        for entry in feed.entries[:limit_per_keyword]:
            title = getattr(entry, "title", "Untitled news")
            url = getattr(entry, "link", "")
            excerpt = getattr(entry, "summary", "")[:300]
            if not url:
                continue

            items.append(
                BuzzItem(
                    title=title,
                    url=url,
                    source="Google News",
                    related_keywords=find_related_keywords(title, keywords) or [keyword],
                    news_count=1,
                    source_excerpt=excerpt,
                )
            )

    return items
