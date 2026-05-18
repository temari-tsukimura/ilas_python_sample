from __future__ import annotations

import json
from pathlib import Path


def load_posted_urls(path: Path) -> set[str]:
    """Load already-posted URLs so the bot does not notify duplicates."""
    if not path.exists():
        return set()

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        return set()

    if isinstance(data, dict):
        urls = data.get("posted_urls", [])
    else:
        urls = data

    return {str(url) for url in urls}


def save_posted_urls(path: Path, urls: set[str]) -> None:
    """Save posted URLs in a stable, readable JSON format."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump({"posted_urls": sorted(urls)}, file, ensure_ascii=False, indent=2)
