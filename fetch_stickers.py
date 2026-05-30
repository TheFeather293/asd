#!/usr/bin/env python3
"""
Fetch all image file URLs from the Bee Swarm Simulator wiki "Sticker" page
via the MediaWiki API (generator=images). Follows continuation until every
batch is retrieved.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_URL = "https://bee-swarm-simulator.fandom.com/api.php"
DEFAULT_TITLE = "Sticker"


def _session_with_retries() -> requests.Session:
    retry = Retry(
        total=5,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    adapter = HTTPAdapter(max_retries=retry)
    s = requests.Session()
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def fetch_all_sticker_images(
    session: requests.Session,
    title: str = DEFAULT_TITLE,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """
    Returns a list of dicts with at least: title, ns, pageid, imageinfo (list).
    """
    params: dict[str, Any] = {
        "action": "query",
        "generator": "images",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json",
        "gimlimit": str(limit),
    }
    headers = {
        "User-Agent": "BSS-StickerFetcher/1.0 (educational; Python requests)",
    }
    pages: dict[str, Any] = {}

    while True:
        resp = session.get(API_URL, params=params, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        batch = data.get("query", {}).get("pages", {})
        for page_id, page in batch.items():
            pages[page_id] = page

        cont = data.get("continue")
        if not cont:
            break
        # Merge continuation tokens into the next request (MediaWiki pattern).
        params.update(cont)

    # Stable sort by numeric page id for reproducible output
    out = list(pages.values())
    out.sort(key=lambda p: int(p.get("pageid", 0)))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--title",
        default=DEFAULT_TITLE,
        help=f'Wiki page title to list images from (default: "{DEFAULT_TITLE}")',
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="gimlimit per request (max 500 on most wikis)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Write JSON to this file (default: stdout)",
    )
    args = parser.parse_args()

    with _session_with_retries() as session:
        pages = fetch_all_sticker_images(session, title=args.title, limit=args.limit)

    payload = {
        "title": args.title,
        "count": len(pages),
        "pages": pages,
    }

    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
