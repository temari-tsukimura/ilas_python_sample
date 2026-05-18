from __future__ import annotations

import argparse
import time
from datetime import datetime, timedelta

from app.ai_summarizer import summarize_items_with_ai
from app.collectors.trends import collect_trends
from app.config import load_filter_rules, load_keywords, load_settings
from app.discord_webhook import post_to_discord
from app.scoring import BuzzItem
from app.storage import load_posted_urls, save_posted_urls


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect anime buzz data and post top items to Discord.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Discordに投稿せず、取得した上位5件をコンソールに表示します。",
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="OpenAI APIを使わずに実行します。API消費を避けたい時に使います。",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="定期実行モードを開始します。",
    )
    return parser.parse_args()


def select_new_top_items(
    items: list[BuzzItem],
    posted_urls: set[str],
    top_n: int,
) -> list[BuzzItem]:
    """Sort items by buzz score and keep only URLs that were not posted before."""
    unique_items: dict[str, BuzzItem] = {}

    for item in items:
        if not item.url or item.url in posted_urls:
            continue

        existing = unique_items.get(item.url)
        if existing is None or item.trend_score > existing.trend_score:
            unique_items[item.url] = item

    sorted_items = sorted(
        unique_items.values(),
        key=lambda item: item.trend_score,
        reverse=True,
    )
    return sorted_items[:top_n]


def count_duplicate_skips(items: list[BuzzItem], posted_urls: set[str]) -> int:
    """Count items skipped because their URL was already posted."""
    return sum(1 for item in items if item.url in posted_urls)


def print_dry_run_items(items: list[BuzzItem]) -> None:
    """Show selected items without sending anything to Discord."""
    if not items:
        print("Dry run result: no new items to post.")
        return

    print("Dry run result: top items that would be posted:")
    for index, item in enumerate(items, start=1):
        keywords = ", ".join(item.related_keywords) if item.related_keywords else "未検出"
        breakdown = ", ".join(
            f"{name}={value}" for name, value in item.breakdown().items()
        )
        print(f"{index}. [{item.source}] {item.title}")
        print(f"   URL: {item.url}")
        print(f"   関連キーワード: {keywords}")
        if item.anilist_status or item.season_year or item.season or item.format:
            print(
                "   放送情報: "
                f"status={item.anilist_status or '-'}, "
                f"year={item.season_year or '-'}, "
                f"season={item.season or '-'}, "
                f"format={item.format or '-'}, "
                f"episodes={item.episodes or '-'}"
            )
        print(f"   話題度スコア: {item.trend_score:.2f}")
        print(f"   内訳: {breakdown}")
        print(f"   AI要約: {item.ai_summary}")
        print(f"   話題の理由: {item.ai_buzz_reason}")
        print(f"   カテゴリ: {item.ai_category}")
        current_related = (
            "不明"
            if item.ai_is_current_season_related is None
            else str(item.ai_is_current_season_related)
        )
        print(f"   今期関連: {current_related}")


def is_placeholder_webhook_url(webhook_url: str) -> bool:
    """Detect the example Discord Webhook URL before making a network call."""
    return (
        "your_webhook_id" in webhook_url
        or "your_webhook_token" in webhook_url
        or webhook_url.strip() == ""
    )


def run_check(
    *,
    args: argparse.Namespace,
    settings,
    keywords: list[str],
    excluded_keywords: list[str],
    filter_rules: dict,
) -> int:
    """Run one collection/posting cycle and return the planned post count."""
    posted_urls = load_posted_urls(settings.posted_items_path)

    check_started_at = datetime.now()
    print(f"Check started at: {check_started_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print("Collecting anime buzz data...")
    result = collect_trends(
        keywords,
        settings.x_bearer_token,
        filter_rules,
        excluded_keywords,
    )
    items = result.items
    top_items = select_new_top_items(items, posted_urls, settings.top_n)
    duplicate_skip_count = count_duplicate_skips(items, posted_urls)

    print(f"Fetched item count: {len(items)}")
    print(f"Duplicate skipped count: {duplicate_skip_count}")
    if args.dry_run:
        print(f"Dry-run display count: {len(top_items)}")
    else:
        print(f"Post count: {len(top_items)}")

    summarize_items_with_ai(
        top_items,
        settings.openai_api_key,
        settings.openai_model,
        disabled=args.no_ai,
    )

    if args.dry_run:
        print_dry_run_items(top_items)
        print("Dry run complete. Discord was not called and posted_items.json was not updated.")
        return len(top_items)

    print(f"Posting {len(top_items)} new item(s) to Discord...")
    post_to_discord(
        settings.discord_webhook_url,
        top_items,
        result.long_running_excluded_count,
    )

    posted_urls.update(item.url for item in top_items)
    save_posted_urls(settings.posted_items_path, posted_urls)
    print("Done.")
    return len(top_items)


def main() -> None:
    args = parse_args()
    settings = load_settings()
    keywords = load_keywords(settings.keywords_path)
    excluded_keywords = load_keywords(settings.excluded_keywords_path)
    filter_rules = load_filter_rules(settings.filter_rules_path)

    if not keywords:
        raise ValueError("No keywords found. Please edit config/trend_keywords.json.")
    if not args.dry_run and is_placeholder_webhook_url(settings.discord_webhook_url):
        raise ValueError(
            "DISCORD_WEBHOOK_URL is not set or still uses the example value. "
            "Copy .env.example to .env and add your real Discord Webhook URL, "
            "or run with --dry-run."
        )

    if not args.watch:
        run_check(
            args=args,
            settings=settings,
            keywords=keywords,
            excluded_keywords=excluded_keywords,
            filter_rules=filter_rules,
        )
        return

    print("Watch mode started.")
    print(f"Current check interval: {settings.check_interval_minutes} minutes")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            run_check(
                args=args,
                settings=settings,
                keywords=keywords,
                excluded_keywords=excluded_keywords,
                filter_rules=filter_rules,
            )
            next_check_at = datetime.now() + timedelta(
                minutes=settings.check_interval_minutes
            )
            print(f"Next check at: {next_check_at.strftime('%Y-%m-%d %H:%M:%S')}")
            time.sleep(settings.check_interval_minutes * 60)
    except KeyboardInterrupt:
        print("Watch mode stopped by Ctrl+C.")


if __name__ == "__main__":
    main()
