# doc-scraper

Scrape the full documentation of any framework or package and generate an **AGENTS.md** file that gives an AI agent comprehensive knowledge of its features.

## Quick start

```bash
# Install
pip install -e ".[dev]"

# Scrape a documentation site
doc-scrape https://docs.agno.com/introduction

# Custom output path and package name
doc-scrape https://docs.agno.com/introduction -o agno_AGENTS.md -n "Agno Framework"
```

## CLI options

| Flag | Default | Description |
|------|---------|-------------|
| `url` | *(required)* | Entry‑point URL of the documentation |
| `-o / --output` | `AGENTS.md` | Output file path |
| `-n / --name` | auto‑detect | Human‑friendly package name |
| `--max-pages` | 500 | Maximum pages to scrape |
| `--delay` | 0.25 | Seconds between HTTP requests |
| `-v / --verbose` | off | Enable debug logging |

## How it works

1. **Crawl** – starting from the given URL, the scraper follows internal navigation links (sidebar, next/prev, etc.) and collects all reachable documentation pages under the same domain‑path scope.
2. **Extract** – for each page it extracts headings, body text, and code examples while discarding chrome (nav, footer, scripts).
3. **Generate** – the collected content is assembled into a structured `AGENTS.md` with a table of contents, per‑page sections, and inline code blocks.

## Development

```bash
pip install -e ".[dev]"
pytest -q
```
