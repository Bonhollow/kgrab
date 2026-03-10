"""Core scraping logic – crawl a documentation site and extract structured content."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PageContent:
    """Represents the extracted content of a single documentation page."""

    url: str
    title: str
    sections: List["Section"] = field(default_factory=list)


@dataclass
class Section:
    """A heading + body block extracted from a page."""

    heading: str
    level: int  # 1–6
    body: str  # plain‑text / markdown body under this heading
    code_blocks: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _same_docs_domain(base_url: str, candidate: str) -> bool:
    """Return True if *candidate* belongs to the same documentation scope."""
    base = urlparse(base_url)
    cand = urlparse(candidate)
    # Same host required
    if base.netloc != cand.netloc:
        return False
    # Use the parent directory of the base path as the scope.
    # e.g. base "/docs/intro" → scope "/docs", base "/intro" → scope "/"
    base_path = base.path.rstrip("/")
    if "/" in base_path:
        scope = base_path.rsplit("/", 1)[0]
    else:
        scope = ""
    if scope:
        return cand.path.startswith(scope + "/") or cand.path == scope
    return True


_SKIP_EXTENSIONS = frozenset([
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
    ".pdf", ".zip", ".tar", ".gz",
    ".css", ".js", ".woff", ".woff2", ".ttf", ".eot",
    ".mp4", ".mp3", ".wav",
])


def _should_skip(url: str) -> bool:
    """Return True for URLs pointing to static assets or anchors-only."""
    parsed = urlparse(url)
    path_lower = parsed.path.lower()
    return any(path_lower.endswith(ext) for ext in _SKIP_EXTENSIONS)


def _extract_nav_links(soup: BeautifulSoup, base_url: str) -> List[str]:
    """Extract links from navigation elements (sidebar, nav bars)."""
    links: List[str] = []
    # Look for common nav containers
    nav_selectors = [
        "nav",
        "[role='navigation']",
        ".sidebar",
        ".side-nav",
        ".menu",
        ".toc",
        ".docs-nav",
        ".docs-sidebar",
    ]
    nav_elements: List[Tag] = []
    for sel in nav_selectors:
        nav_elements.extend(soup.select(sel))

    for nav in nav_elements:
        for a_tag in nav.find_all("a", href=True):
            href = a_tag["href"]
            absolute = urljoin(base_url, href)
            absolute = urldefrag(absolute)[0]  # strip fragment
            links.append(absolute)
    return links


def _extract_all_links(soup: BeautifulSoup, base_url: str) -> List[str]:
    """Extract every <a href> from the page, resolved to absolute URLs."""
    links: List[str] = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        absolute = urljoin(base_url, href)
        absolute = urldefrag(absolute)[0]
        links.append(absolute)
    return links


def _extract_content(soup: BeautifulSoup, url: str) -> PageContent:
    """Parse a BeautifulSoup tree and return structured PageContent."""
    # Determine title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else url

    # Try to locate the main content area
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find("div", class_="content")
        or soup.find("div", class_="docs-content")
        or soup.find("div", id="content")
        or soup.find("div", {"role": "main"})
        or soup.body
    )
    if main is None:
        return PageContent(url=url, title=title)

    # Remove nav, footer, header, script, style elements from main
    for tag_name in ("nav", "footer", "header", "script", "style", "noscript"):
        for tag in main.find_all(tag_name):
            tag.decompose()

    sections: List[Section] = []
    current_heading = "Introduction"
    current_level = 1
    current_body_parts: List[str] = []
    current_code_blocks: List[str] = []

    for element in main.descendants:
        if not isinstance(element, Tag):
            continue

        if element.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            # Save previous section
            body_text = "\n".join(current_body_parts).strip()
            if body_text or current_code_blocks:
                sections.append(Section(
                    heading=current_heading,
                    level=current_level,
                    body=body_text,
                    code_blocks=list(current_code_blocks),
                ))
            current_heading = element.get_text(strip=True)
            current_level = int(element.name[1])
            current_body_parts = []
            current_code_blocks = []

        elif element.name == "pre":
            code_tag = element.find("code")
            code_text = code_tag.get_text() if code_tag else element.get_text()
            current_code_blocks.append(code_text.strip())

        elif element.name == "p":
            text = element.get_text(strip=True)
            if text:
                current_body_parts.append(text)

        elif element.name == "li":
            text = element.get_text(strip=True)
            if text:
                current_body_parts.append(f"- {text}")

    # Flush last section
    body_text = "\n".join(current_body_parts).strip()
    if body_text or current_code_blocks:
        sections.append(Section(
            heading=current_heading,
            level=current_level,
            body=body_text,
            code_blocks=list(current_code_blocks),
        ))

    return PageContent(url=url, title=title, sections=sections)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass
class ScrapeResult:
    """Aggregated scrape output."""

    pages: List[PageContent] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)


def scrape_docs(
    start_url: str,
    *,
    max_pages: int = 500,
    delay: float = 0.25,
    timeout: int = 15,
    headers: Optional[Dict[str, str]] = None,
) -> ScrapeResult:
    """Crawl documentation starting from *start_url* and return extracted content.

    Parameters
    ----------
    start_url:
        The entry‑point URL of the documentation (e.g. ``https://docs.agno.com/introduction``).
    max_pages:
        Safety cap on the number of pages to fetch.
    delay:
        Seconds to wait between requests (be polite).
    timeout:
        HTTP request timeout in seconds.
    headers:
        Optional extra HTTP headers.

    Returns
    -------
    ScrapeResult
        Collected pages and any per‑URL errors.
    """
    result = ScrapeResult()
    visited: Set[str] = set()
    queue: List[str] = [urldefrag(start_url)[0]]
    request_headers = {
        "User-Agent": "doc-scraper/0.1 (documentation indexer)",
    }
    if headers:
        request_headers.update(headers)

    while queue and len(result.pages) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        if _should_skip(url):
            continue
        if not _same_docs_domain(start_url, url):
            continue

        visited.add(url)
        logger.info("Fetching %s  (%d/%d)", url, len(result.pages) + 1, max_pages)

        try:
            resp = requests.get(url, headers=request_headers, timeout=timeout)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Failed to fetch %s: %s", url, exc)
            result.errors[url] = str(exc)
            continue

        content_type = resp.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        page = _extract_content(soup, url)
        result.pages.append(page)

        # Discover links – prefer navigation links, fall back to all links
        nav_links = _extract_nav_links(soup, url)
        all_links = _extract_all_links(soup, url)
        candidates = nav_links if nav_links else all_links
        for link in candidates:
            if link not in visited and _same_docs_domain(start_url, link):
                if link not in queue:
                    queue.append(link)

        # Also add all links so we don't miss pages not in nav
        for link in all_links:
            if link not in visited and _same_docs_domain(start_url, link):
                if link not in queue:
                    queue.append(link)

        if delay:
            time.sleep(delay)

    return result
