"""
Download all AEYE Health LinkedIn posts from the last two years to a JSON file.

Uses LinkedIn's official REST API (Marketing Developer Platform).

Setup:
  1. Create a LinkedIn app at https://www.linkedin.com/developers/apps
  2. Request Marketing Developer Platform access and the `r_organization_social`
     OAuth scope. AEYE Health admins must authorize the app against the company
     page (organization ID 18116152 — verify via the Organization Lookup API).
  3. Obtain a 3-legged OAuth access token and export it:
         export LINKEDIN_ACCESS_TOKEN=...
         export AEYE_ORG_ID=18116152          # optional, default below
  4. pip install -r requirements.txt
  5. python download_aeye_posts.py [--output posts.json]

Without an access token + approved app, LinkedIn will return 401/403. There is
no public, anonymous endpoint for company posts.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests

API_BASE = "https://api.linkedin.com/rest/posts"
API_VERSION = "202506"
DEFAULT_ORG_ID = "18116152"
PAGE_SIZE = 100


def fetch_page(token: str, org_urn: str, start: int) -> dict:
    params = {
        "q": "author",
        "author": org_urn,
        "count": PAGE_SIZE,
        "start": start,
        "sortBy": "LAST_MODIFIED",
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "LinkedIn-Version": API_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }
    url = f"{API_BASE}?{urlencode(params)}"
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code == 429:
        retry_after = int(resp.headers.get("Retry-After", "30"))
        time.sleep(retry_after)
        return fetch_page(token, org_urn, start)
    resp.raise_for_status()
    return resp.json()


def download_posts(token: str, org_id: str, cutoff_ms: int) -> list[dict]:
    org_urn = f"urn:li:organization:{org_id}"
    posts: list[dict] = []
    start = 0
    while True:
        page = fetch_page(token, org_urn, start)
        elements = page.get("elements", [])
        if not elements:
            break

        stop = False
        for post in elements:
            created = post.get("createdAt") or post.get("publishedAt") or 0
            if created and created < cutoff_ms:
                stop = True
                continue
            posts.append(post)

        paging = page.get("paging", {})
        total = paging.get("total")
        next_start = start + len(elements)
        if stop or not elements or (total is not None and next_start >= total):
            break
        start = next_start
    return posts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="aeye_health_posts.json")
    parser.add_argument(
        "--org-id",
        default=os.environ.get("AEYE_ORG_ID", DEFAULT_ORG_ID),
        help="LinkedIn organization ID for AEYE Health",
    )
    parser.add_argument("--years", type=int, default=2)
    args = parser.parse_args()

    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    if not token:
        print("ERROR: set LINKEDIN_ACCESS_TOKEN env var", file=sys.stderr)
        return 1

    cutoff = datetime.now(timezone.utc) - timedelta(days=365 * args.years)
    cutoff_ms = int(cutoff.timestamp() * 1000)

    posts = download_posts(token, args.org_id, cutoff_ms)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(
            {
                "organization_id": args.org_id,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "cutoff": cutoff.isoformat(),
                "count": len(posts),
                "posts": posts,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"Saved {len(posts)} posts to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
