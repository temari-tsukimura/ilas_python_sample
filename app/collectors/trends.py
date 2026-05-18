from __future__ import annotations

from dataclasses import dataclass

from app.collectors.anilist import fetch_popular_anime
from app.collectors.news import fetch_google_news
from app.collectors.reddit import fetch_reddit_posts
from app.collectors.twitter_reactions import fetch_twitter_reaction_score
from app.scoring import BuzzItem


@dataclass
class TrendCollectionResult:
    items: list[BuzzItem]
    long_running_excluded_count: int = 0


def collect_trends(
    keywords: list[str],
    x_bearer_token: str | None,
    filter_rules: dict,
    excluded_keywords: list[str],
) -> TrendCollectionResult:
    """Collect buzz items from each source without stopping on one failure."""
    items: list[BuzzItem] = []
    long_running_excluded_count = 0

    try:
        anilist_items, excluded_count = fetch_popular_anime(
            keywords,
            filter_rules,
            excluded_keywords,
        )
        items.extend(anilist_items)
        long_running_excluded_count += excluded_count
    except Exception as error:
        print(f"AniList collector skipped because of an unexpected error: {error}")

    for collector in [lambda: fetch_google_news(keywords), lambda: fetch_reddit_posts(keywords)]:
        try:
            items.extend(collector())
        except Exception as error:
            print(f"Collector skipped because of an unexpected error: {error}")

    if x_bearer_token:
        add_twitter_scores(items, keywords, x_bearer_token)
    else:
        print("X_BEARER_TOKEN is not set. Skipping X/Twitter reaction score.")

    return TrendCollectionResult(
        items=items,
        long_running_excluded_count=long_running_excluded_count,
    )


def add_twitter_scores(
    items: list[BuzzItem],
    keywords: list[str],
    x_bearer_token: str,
) -> None:
    """Add optional X/Twitter scores to items with matching keywords."""
    score_cache: dict[str, float] = {}

    for item in items:
        target_keywords = item.related_keywords or [
            keyword for keyword in keywords if keyword.lower() in item.title.lower()
        ]
        if not target_keywords:
            continue

        total_score = 0.0
        for keyword in target_keywords[:3]:
            if keyword not in score_cache:
                score_cache[keyword] = fetch_twitter_reaction_score(
                    keyword,
                    x_bearer_token,
                )
            total_score += score_cache[keyword]

        item.twitter_reaction_score = total_score
