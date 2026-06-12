"""Fetch and extract readable text from web pages.

Two entry points:
  - fetch_page(url): grab one page, return {url, title, text}
  - crawl_site(url, max_pages): follow same-domain links from a starting page
    so we can read "all the pages" of a company website for voice analysis.

Scraping runs server-side (via requests) so the browser's CORS restrictions
don't get in the way — the user just supplies URLs.
"""

from __future__ import annotations

from collections import deque
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; CompanyVoiceBot/1.0; +https://example.com/bot)"
    )
}
TIMEOUT = 20
# Strip these tags before extracting text — they're navigation/chrome, not prose.
_NOISE_TAGS = ["script", "style", "noscript", "nav", "footer", "header", "form",
               "aside", "svg", "iframe"]


class ScrapeError(Exception):
    pass


def _normalise(url: str) -> str:
    """Add a scheme if missing and drop the #fragment."""
    url = url.strip()
    if not url:
        return url
    if not urlparse(url).scheme:
        url = "https://" + url
    return urldefrag(url)[0]


def _extract(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    og = soup.find("meta", property="og:title")
    if not title and og and og.get("content"):
        title = og["content"].strip()

    for tag in soup(_NOISE_TAGS):
        tag.decompose()

    text = soup.get_text(separator="\n")
    # Collapse blank lines / stray whitespace.
    lines = [ln.strip() for ln in text.splitlines()]
    text = "\n".join(ln for ln in lines if ln)
    return title, text


def fetch_page(url: str) -> dict:
    url = _normalise(url)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise ScrapeError(f"Could not fetch {url}: {exc}") from exc

    ctype = resp.headers.get("Content-Type", "")
    if "html" not in ctype and "<html" not in resp.text[:500].lower():
        raise ScrapeError(f"{url} did not return an HTML page (Content-Type: {ctype})")

    title, text = _extract(resp.text)
    if not text:
        raise ScrapeError(f"No readable text found at {url}")
    return {"url": resp.url, "title": title or resp.url, "text": text}


def _same_site(a: str, b: str) -> bool:
    na, nb = urlparse(a).netloc.lower(), urlparse(b).netloc.lower()
    na = na[4:] if na.startswith("www.") else na
    nb = nb[4:] if nb.startswith("www.") else nb
    return na == nb


def _links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        full = _normalise(urljoin(base_url, href))
        if full and _same_site(full, base_url):
            out.append(full)
    return out


# File extensions we never want to crawl into.
_SKIP_EXT = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip", ".mp4",
             ".mp3", ".webp", ".ico", ".css", ".js", ".xml", ".json")


def crawl_site(start_url: str, max_pages: int = 15) -> list[dict]:
    """Breadth-first crawl within one domain, returning extracted pages.

    Returns whatever it managed to read; raises ScrapeError only if even the
    starting page can't be fetched.
    """
    start_url = _normalise(start_url)
    seen: set[str] = set()
    queue: deque[str] = deque([start_url])
    pages: list[dict] = []

    # The starting page must work — surface its error directly.
    first = fetch_page(start_url)
    pages.append(first)
    seen.add(start_url)
    seen.add(first["url"])

    try:
        resp = requests.get(start_url, headers=HEADERS, timeout=TIMEOUT)
        for link in _links(resp.text, start_url):
            if link not in seen and not link.lower().endswith(_SKIP_EXT):
                queue.append(link)
    except requests.RequestException:
        return pages

    while queue and len(pages) < max_pages:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        try:
            page = fetch_page(url)
        except ScrapeError:
            continue
        pages.append(page)
        seen.add(page["url"])

    return pages
