from __future__ import annotations

import feedparser
import requests

from app.scoring import BuzzItem, find_related_keywords


REDDIT_RSS_URL = "https://www.reddit.com/r/anime/hot/.rss"


def fetch_reddit_posts(keywords: list[str], limit: int = 10) -> list[BuzzItem]:
    """Fetch popular posts from r/anime RSS."""
    try:
        response = requests.get(
            REDDIT_RSS_URL,
            headers={"User-Agent": "AnimeBuzzWatcher/1.0"},
            timeout=8,
        )
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except Exception as error:
        print(f"Reddit collector failed: {error}")
        return []

    if getattr(feed, "bozo", False):
        print(f"Reddit RSS parse warning: {feed.bozo_exception}")

    items: list[BuzzItem] = []
    for entry in feed.entries[:limit]:
        title = getattr(entry, "title", "Untitled Reddit post")
        url = getattr(entry, "link", "")
        excerpt = getattr(entry, "summary", "")[:300]
        if not url:
            continue

        # Reddit RSS does not always expose score/comment totals,
        # so this MVP uses a fixed value plus keyword matches as a light signal.
        keyword_matches = find_related_keywords(title, keywords)
        reddit_reactions = 10 + len(keyword_matches) * 5

        items.append(
            BuzzItem(
                title=title,
                url=url,
                source="Reddit r/anime",
                related_keywords=keyword_matches,
                reddit_reactions=reddit_reactions,
                source_excerpt=excerpt,
            )
        )

    return items
