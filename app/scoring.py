from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class BuzzItem:
    title: str
    url: str
    source: str
    related_keywords: list[str] = field(default_factory=list)
    anilist_popularity: float = 0
    news_count: float = 0
    reddit_reactions: float = 0
    twitter_reaction_score: float = 0
    source_excerpt: str = ""
    anilist_status: str | None = None
    season_year: int | None = None
    season: str | None = None
    format: str | None = None
    episodes: int | None = None
    ai_summary: str = "AI要約なし"
    ai_buzz_reason: str = "AI要約なし"
    ai_is_current_season_related: bool | None = None
    ai_category: str = "AI要約なし"
    current_season_bonus: float = 0
    releasing_bonus: float = 0
    recent_year_bonus: float = 0
    old_title_penalty: float = 0
    long_running_penalty: float = 0

    @property
    def trend_score(self) -> float:
        return (
            self.anilist_popularity
            + self.news_count
            + self.reddit_reactions
            + self.twitter_reaction_score
            + self.current_season_bonus
            + self.releasing_bonus
            + self.recent_year_bonus
            - self.old_title_penalty
            - self.long_running_penalty
        )

    def breakdown(self) -> dict[str, float]:
        return {
            "AniList人気度": round(self.anilist_popularity, 2),
            "ニュース件数": round(self.news_count, 2),
            "Reddit反応": round(self.reddit_reactions, 2),
            "X/Twitter反応": round(self.twitter_reaction_score, 2),
            "今期ボーナス": round(self.current_season_bonus, 2),
            "放送中ボーナス": round(self.releasing_bonus, 2),
            "最近の作品ボーナス": round(self.recent_year_bonus, 2),
        }


def calculate_twitter_reaction_score(
    post_count: int,
    like_count: int,
    retweet_count: int,
    reply_count: int,
    quote_count: int,
) -> float:
    """Calculate the optional X/Twitter reaction score from public metrics."""
    return (
        post_count * 1
        + like_count * 0.1
        + retweet_count * 0.5
        + reply_count * 0.3
        + quote_count * 0.4
    )


def find_related_keywords(text: str, keywords: list[str]) -> list[str]:
    """Find configured keywords included in an item's title or description."""
    lowered_text = text.lower()
    return [keyword for keyword in keywords if keyword.lower() in lowered_text]


def get_current_anime_season(today: date | None = None) -> tuple[int, str]:
    """Return AniList-style season name for the current date."""
    today = today or date.today()
    if today.month in (1, 2, 3):
        season = "WINTER"
    elif today.month in (4, 5, 6):
        season = "SPRING"
    elif today.month in (7, 8, 9):
        season = "SUMMER"
    else:
        season = "FALL"
    return today.year, season


def has_excluded_keyword(title_text: str, excluded_keywords: list[str]) -> bool:
    """Return True when a title matches an excluded long-running franchise."""
    lowered_title = title_text.lower()
    return any(keyword.lower() in lowered_title for keyword in excluded_keywords)


def calculate_anilist_season_adjustments(
    *,
    status: str | None,
    season_year: int | None,
    season: str | None,
    episodes: int | None,
    filter_rules: dict,
) -> dict[str, float]:
    """Calculate bonuses and penalties that favor recent/current anime."""
    current_year, current_season = get_current_anime_season()
    max_old_years = int(filter_rules.get("max_old_season_years", 2))
    max_episode_count = int(filter_rules.get("max_episode_count", 100))

    current_season_bonus = 0.0
    releasing_bonus = 0.0
    recent_year_bonus = 0.0
    old_title_penalty = 0.0
    long_running_penalty = 0.0

    if filter_rules.get("prefer_current_season", True):
        if season_year == current_year and season == current_season:
            current_season_bonus = 80.0
        elif season_year == current_year:
            current_season_bonus = 40.0

    if filter_rules.get("prefer_releasing", True) and status == "RELEASING":
        releasing_bonus = 60.0

    if season_year == current_year:
        recent_year_bonus = 50.0
    elif season_year == current_year - 1:
        recent_year_bonus = 20.0
    elif season_year is None:
        old_title_penalty = 30.0
    elif current_year - season_year >= max_old_years:
        old_title_penalty = 120.0

    if episodes is not None and episodes >= max_episode_count:
        long_running_penalty = 150.0

    return {
        "current_season_bonus": current_season_bonus,
        "releasing_bonus": releasing_bonus,
        "recent_year_bonus": recent_year_bonus,
        "old_title_penalty": old_title_penalty,
        "long_running_penalty": long_running_penalty,
    }


def should_exclude_anilist_title(
    *,
    title_text: str,
    season_year: int | None,
    episodes: int | None,
    filter_rules: dict,
    excluded_keywords: list[str],
) -> bool:
    """Apply hard filters for known evergreen titles and very old long series."""
    current_year, _ = get_current_anime_season()
    max_old_years = int(filter_rules.get("max_old_season_years", 2))
    max_episode_count = int(filter_rules.get("max_episode_count", 100))

    if has_excluded_keyword(title_text, excluded_keywords):
        return True

    if (
        filter_rules.get("exclude_long_running", True)
        and episodes is not None
        and episodes >= max_episode_count
        and season_year is not None
        and current_year - season_year >= max_old_years
    ):
        return True

    if season_year is not None and current_year - season_year > max_old_years:
        return True

    return False
