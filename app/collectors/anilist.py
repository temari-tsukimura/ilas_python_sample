from __future__ import annotations

import requests

from app.scoring import (
    BuzzItem,
    calculate_anilist_season_adjustments,
    find_related_keywords,
    get_current_anime_season,
    should_exclude_anilist_title,
)


ANILIST_API_URL = "https://graphql.anilist.co"



def fetch_popular_anime(
    keywords: list[str],
    filter_rules: dict,
    excluded_keywords: list[str],
    limit: int = 25,
) -> tuple[list[BuzzItem], int]:
    """Fetch recent/current popular anime from the AniList GraphQL API."""
    current_year, current_season = get_current_anime_season()
    query = """
    query ($page: Int, $perPage: Int, $seasonYear: Int, $season: MediaSeason) {
      Page(page: $page, perPage: $perPage) {
        media(
          type: ANIME,
          sort: TRENDING_DESC,
          seasonYear: $seasonYear,
          season: $season,
          format_in: [TV, TV_SHORT, MOVIE],
          status_in: [RELEASING, FINISHED, NOT_YET_RELEASED]
        ) {
          id
          title {
            romaji
            english
            native
          }
          siteUrl
          format
          status
          season
          seasonYear
          episodes
          popularity
          trending
        }
      }
    }
    """
    season_queries = [
        {"seasonYear": current_year, "season": current_season},
        {"seasonYear": current_year, "season": None},
        {"seasonYear": current_year - 1, "season": None},
        {"seasonYear": None, "season": None},
    ]

    media_by_id: dict[int, dict] = {}
    for season_query in season_queries:
        variables = {"page": 1, "perPage": limit, **season_query}
        try:
            response = requests.post(
                ANILIST_API_URL,
                json={"query": query, "variables": variables},
                timeout=20,
            )
            response.raise_for_status()
            media_list = response.json()["data"]["Page"]["media"]
        except Exception as error:
            print(f"AniList collector failed: {error}")
            continue

        for media in media_list:
            media_by_id[media["id"]] = media

    items: list[BuzzItem] = []
    excluded_count = 0
    for media in media_by_id.values():
        title_data = media.get("title") or {}
        title = (
            title_data.get("native")
            or title_data.get("english")
            or title_data.get("romaji")
            or "Untitled anime"
        )
        search_text = " ".join(str(value) for value in title_data.values() if value)
        season_year = media.get("seasonYear")
        episodes = media.get("episodes")

        if should_exclude_anilist_title(
            title_text=search_text,
            season_year=season_year,
            episodes=episodes,
            filter_rules=filter_rules,
            excluded_keywords=excluded_keywords,
        ):
            excluded_count += 1
            continue

        # Scale AniList popularity down a little so season bonuses can affect ranking.
        popularity = float(media.get("trending") or media.get("popularity") or 0)
        popularity_score = popularity * 0.8
        adjustments = calculate_anilist_season_adjustments(
            status=media.get("status"),
            season_year=season_year,
            season=media.get("season"),
            episodes=episodes,
            filter_rules=filter_rules,
        )

        items.append(
            BuzzItem(
                title=title,
                url=media.get("siteUrl") or f"https://anilist.co/anime/{media['id']}",
                source="AniList",
                related_keywords=find_related_keywords(search_text, keywords),
                anilist_popularity=popularity_score,
                anilist_status=media.get("status"),
                season_year=season_year,
                season=media.get("season"),
                format=media.get("format"),
                episodes=episodes,
                source_excerpt=(
                    f"AniList status={media.get('status')}, "
                    f"seasonYear={season_year}, season={media.get('season')}, "
                    f"format={media.get('format')}, episodes={episodes}"
                ),
                current_season_bonus=adjustments["current_season_bonus"],
                releasing_bonus=adjustments["releasing_bonus"],
                recent_year_bonus=adjustments["recent_year_bonus"],
                old_title_penalty=adjustments["old_title_penalty"],
                long_running_penalty=adjustments["long_running_penalty"],
            )
        )

    return items, excluded_count
