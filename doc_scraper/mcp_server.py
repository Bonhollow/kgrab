"""MCP (Model Context Protocol) server exposing doc-scraper tools."""

from __future__ import annotations

import pathlib
from mcp.server.fastmcp import FastMCP

from .scraper import scrape_docs
from .agents_generator import generate_agents_md

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "doc-scraper",
    description="Scrape framework/package documentation and generate an AGENTS.md knowledge file.",
)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def scrape_documentation(
    url: str,
    max_pages: int = 500,
    package_name: str | None = None,
    output_path: str = "AGENTS.md",
    compact: bool = True,
) -> str:
    """Scrape ALL documentation from a framework/package URL and generate an AGENTS.md file.

    Args:
        url: Entry-point URL of the documentation site (e.g. https://docs.agno.com/introduction).
        max_pages: Maximum number of pages to scrape (default 500).
        package_name: Human-friendly package name. Auto-detected from the page title if omitted.
        output_path: File path where the AGENTS.md will be written (default ./AGENTS.md).
        compact: Compress output by truncating prose and code blocks (default True).

    Returns:
        A summary of how many pages were scraped and where the file was saved.
    """
    result = scrape_docs(url, max_pages=max_pages, delay=0.25)

    md = generate_agents_md(result, package_name=package_name, compact=compact)

    out = pathlib.Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")

    return (
        f"✅ Scraped {len(result.pages)} page(s) from {url}\n"
        f"⚠️ {len(result.errors)} error(s)\n"
        f"📄 AGENTS.md written to {out.resolve()} ({len(md)} bytes)"
    )


@mcp.tool()
async def scrape_documentation_to_text(
    url: str,
    max_pages: int = 500,
    package_name: str | None = None,
    compact: bool = True,
) -> str:
    """Scrape documentation and return the AGENTS.md content as text (without saving to disk).

    Args:
        url: Entry-point URL of the documentation site.
        max_pages: Maximum number of pages to scrape (default 500).
        package_name: Human-friendly package name. Auto-detected if omitted.
        compact: Compress output by truncating prose and code blocks (default True).

    Returns:
        The AGENTS.md markdown content.
    """
    result = scrape_docs(url, max_pages=max_pages, delay=0.25)
    return generate_agents_md(result, package_name=package_name, compact=compact)


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
