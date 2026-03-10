"""Command‑line interface for doc_scraper."""

from __future__ import annotations

import argparse
import logging
import pathlib
import sys

from .scraper import scrape_docs
from .agents_generator import generate_agents_md


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="doc-scrape",
        description="Scrape framework/package documentation and generate an AGENTS.md file.",
    )
    parser.add_argument(
        "url",
        help="Entry‑point URL of the documentation site (e.g. https://docs.agno.com/introduction).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="AGENTS.md",
        help="Path for the generated AGENTS.md file (default: ./AGENTS.md).",
    )
    parser.add_argument(
        "-n",
        "--name",
        default=None,
        help="Human‑friendly package name (auto‑detected if omitted).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=500,
        help="Maximum number of pages to scrape (default: 500).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.25,
        help="Delay in seconds between HTTP requests (default: 0.25).",
    )
    parser.add_argument(
        "-c",
        "--compact",
        action="store_true",
        help="Compress output: truncate prose to 2 sentences/section, cap code to 10 lines.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose / debug logging.",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    logging.info("Starting scrape from %s …", args.url)
    result = scrape_docs(
        args.url,
        max_pages=args.max_pages,
        delay=args.delay,
    )

    logging.info("Scraped %d page(s), %d error(s).", len(result.pages), len(result.errors))

    md = generate_agents_md(result, package_name=args.name, compact=args.compact)

    out_path = pathlib.Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")

    logging.info("Wrote %s (%d bytes).", out_path, len(md))


if __name__ == "__main__":
    main()
