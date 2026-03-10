"""Generate an AGENTS.md file from scraped documentation content."""

from __future__ import annotations

import re
from typing import List, Set

from .scraper import PageContent, ScrapeResult, Section


def _slugify(text: str) -> str:
    """Create a simple markdown-anchor-friendly slug."""
    return (
        text.lower()
        .replace(" ", "-")
        .replace(".", "")
        .replace("(", "")
        .replace(")", "")
        .replace("/", "")
        .replace(":", "")
        .replace("'", "")
        .replace('"', "")
    )


# ---------------------------------------------------------------------------
# Compact-mode helpers
# ---------------------------------------------------------------------------

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

# Common boilerplate patterns to strip from body text
_BOILERPLATE_PATTERNS = [
    re.compile(r"©\s*\d{4}.*$", re.IGNORECASE),
    re.compile(r"All rights reserved\.?", re.IGNORECASE),
    re.compile(r"^(Was this page helpful|Give us feedback|Edit this page|Next\s*→|Previous\s*←).*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^(Sign up|Log in|Subscribe|Newsletter).*$", re.IGNORECASE | re.MULTILINE),
]

# Words that signal a page is a thin index/redirect with no real content
_THIN_PAGE_INDICATORS = frozenset([
    "overview", "index", "table of contents",
])


def _clean_title(title: str) -> str:
    """Strip common site-name suffixes like ' - Agno' or ' | Docs'."""
    for sep in (" — ", " | ", " - ", " – "):
        if sep in title:
            parts = title.split(sep)
            # Keep only the first part (the actual page name)
            return parts[0].strip()
    return title.strip()


def _strip_boilerplate(text: str) -> str:
    """Remove boilerplate lines from extracted text."""
    for pat in _BOILERPLATE_PATTERNS:
        text = pat.sub("", text)
    return text.strip()


def _is_thin_page(page: PageContent) -> bool:
    """Return True if the page contains very little substantive content."""
    total_body = sum(len(s.body) for s in page.sections)
    total_code = sum(len(c) for s in page.sections for c in s.code_blocks)
    # If less than 50 chars of text and no code, it's thin
    return total_body < 50 and total_code == 0


def _truncate_body(body: str, max_sentences: int = 2) -> str:
    """Keep only the first *max_sentences* sentences of a body paragraph."""
    if not body:
        return body
    sentences = _SENTENCE_RE.split(body)
    if len(sentences) <= max_sentences:
        return body
    return " ".join(sentences[:max_sentences]).rstrip() + " …"


def _truncate_code(code: str, max_lines: int = 10) -> str:
    """Cap a code block to *max_lines* lines."""
    lines = code.splitlines()
    if len(lines) <= max_lines:
        return code
    return "\n".join(lines[:max_lines]) + "\n# … (truncated)"


def _deduplicate_sections(sections: List[Section]) -> List[Section]:
    """Remove sections whose body text is identical to a previous section."""
    seen: Set[str] = set()
    unique: List[Section] = []
    for s in sections:
        key = s.body.strip()[:200]  # compare first 200 chars
        if key and key in seen:
            continue
        seen.add(key)
        unique.append(s)
    return unique


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English text."""
    return len(text) // 4


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_agents_md(
    result: ScrapeResult,
    package_name: str | None = None,
    *,
    compact: bool = False,
    max_sentences: int = 2,
    max_code_lines: int = 10,
) -> str:
    """Return the full text of an ``AGENTS.md`` file.

    Parameters
    ----------
    result:
        Output of :func:`scrape_docs`.
    package_name:
        Human-friendly name for the package (auto-detected if *None*).
    compact:
        When True, aggressively compress output by:
        - removing thin/empty pages,
        - stripping boilerplate text,
        - deduplicating sections,
        - truncating body text to *max_sentences* per section,
        - capping code blocks to *max_code_lines*,
        - keeping only the first code block per section,
        - cleaning up page titles.
    max_sentences:
        Sentences to keep per section body in compact mode (default 2).
    max_code_lines:
        Lines to keep per code block in compact mode (default 10).

    Returns
    -------
    str
        Markdown text ready to be written to disk.
    """
    if not result.pages:
        return "# AGENTS.md\n\nNo documentation pages were found.\n"

    # Auto-detect package name from the first page title if not provided
    if package_name is None:
        first_title = result.pages[0].title
        for sep in (" — ", " | ", " - ", " – "):
            if sep in first_title:
                package_name = first_title.split(sep)[0].strip()
                break
        else:
            package_name = first_title

    # ----- Pre-process pages in compact mode -----
    pages = list(result.pages)
    if compact:
        # 1. Filter out thin/empty pages
        pages = [p for p in pages if not _is_thin_page(p)]

        # 2. Deduplicate pages by cleaned title (keep first occurrence)
        seen_titles: Set[str] = set()
        deduped: List[PageContent] = []
        for p in pages:
            clean = _clean_title(p.title).lower()
            if clean in seen_titles:
                continue
            seen_titles.add(clean)
            deduped.append(p)
        pages = deduped

    lines: List[str] = []

    # Header
    lines.append(f"# {package_name} – Agent Knowledge Base\n")
    mode_label = "compact" if compact else "full"
    total_pages = len(result.pages)
    kept_pages = len(pages)
    token_note = ""
    lines.append(
        f"> Auto-generated from the official documentation. "
        f"{total_pages} page(s) scraped"
        + (f", {kept_pages} kept after filtering" if compact else "")
        + f". Mode: **{mode_label}**.\n"
    )

    # Table of contents -------------------------------------------------
    lines.append("## Table of Contents\n")
    for page in pages:
        title = _clean_title(page.title) if compact else page.title
        slug = _slugify(title)
        lines.append(f"- [{title}](#{slug})")
    lines.append("")

    # Per-page content ---------------------------------------------------
    for page in pages:
        title = _clean_title(page.title) if compact else page.title
        lines.append(f"---\n")
        lines.append(f"## {title}\n")
        lines.append(f"*Source: {page.url}*\n")

        sections = page.sections
        if compact:
            sections = _deduplicate_sections(sections)

        for section in sections:
            md_level = min(section.level + 2, 6)
            prefix = "#" * md_level
            lines.append(f"{prefix} {section.heading}\n")

            body = section.body
            code_blocks = section.code_blocks

            if compact:
                body = _strip_boilerplate(body)
                body = _truncate_body(body, max_sentences)
                # Keep only the first code block, truncated
                code_blocks = (
                    [_truncate_code(code_blocks[0], max_code_lines)]
                    if code_blocks
                    else []
                )

            if body:
                lines.append(body)
                lines.append("")

            for code in code_blocks:
                lines.append("```")
                lines.append(code)
                lines.append("```\n")

    # Errors section (if any) -------------------------------------------
    if result.errors:
        lines.append("---\n")
        lines.append("## ⚠️ Pages that could not be fetched\n")
        for url, err in result.errors.items():
            lines.append(f"- **{url}**: {err}")
        lines.append("")

    md = "\n".join(lines) + "\n"

    # Append token estimate as a footer
    tokens = _estimate_tokens(md)
    md += f"\n---\n*Estimated tokens: ~{tokens:,}*\n"

    return md
