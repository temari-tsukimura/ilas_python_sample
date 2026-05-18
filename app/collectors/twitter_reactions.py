from __future__ import annotations

import requests

from app.scoring import calculate_twitter_reaction_score


X_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"


def fetch_twitter_reaction_score(keyword: str, bearer_token: str | None) -> float:
    """Fetch optional X/Twitter reaction score for one keyword.

    This function only runs when X_BEARER_TOKEN exists. It uses the official
    X API and never scrapes pages.
    """
    if not bearer_token:
        return 0

    params = {
        "query": f'"{keyword}" lang:ja -is:retweet',
        "max_results": 20,
        "tweet.fields": "public_metrics",
    }
    headers = {"Authorization": f"Bearer {bearer_token}"}

    try:
        response = requests.get(X_SEARCH_URL, params=params, headers=headers, timeout=20)
        response.raise_for_status()
        tweets = response.json().get("data", [])
    except Exception as error:
        print(f"X/Twitter collector failed for {keyword}: {error}")
        return 0

    like_count = 0
    retweet_count = 0
    reply_count = 0
    quote_count = 0

    for tweet in tweets:
        metrics = tweet.get("public_metrics", {})
        like_count += int(metrics.get("like_count", 0))
        retweet_count += int(metrics.get("retweet_count", 0))
        reply_count += int(metrics.get("reply_count", 0))
        quote_count += int(metrics.get("quote_count", 0))

    return calculate_twitter_reaction_score(
        post_count=len(tweets),
        like_count=like_count,
        retweet_count=retweet_count,
        reply_count=reply_count,
        quote_count=quote_count,
    )
