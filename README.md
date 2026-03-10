<p align="center">
  <img src="logo.png" alt="kgrab logo" width="500">
</p>

<p align="center">
  <strong>Scrape any framework's documentation and generate an AGENTS.md knowledge file for AI agents.</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/kgrab/"><img src="https://img.shields.io/pypi/v/kgrab?color=blue" alt="PyPI"></a>
  <a href="https://github.com/Bonhollow/kgrab"><img src="https://img.shields.io/github/stars/Bonhollow/kgrab?style=social" alt="GitHub Stars"></a>
  <a href="https://github.com/Bonhollow/kgrab/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Bonhollow/kgrab" alt="License"></a>
</p>

---

## What is kgrab?

**kgrab** crawls the full documentation of any framework or package and generates a structured `AGENTS.md` file — a knowledge base that makes AI agents aware of all the features, APIs, and patterns of a library.

It works as a **CLI tool**, a **pip package**, and an **MCP server** (Model Context Protocol) so AI assistants like Claude, Gemini, or Cursor can call it as a tool.

---

## Quick Start

```bash
pip install kgrab
```

### CLI usage

```bash
# Scrape docs and generate AGENTS.md
doc-scrape https://docs.agno.com/introduction

# Compact mode (70% smaller output)
doc-scrape https://docs.agno.com/introduction --compact

# Custom output path and package name
doc-scrape https://docs.agno.com/introduction -o agno_AGENTS.md -n "Agno" --compact
```

### MCP server usage

Add to your MCP client config (Claude Desktop, Gemini CLI, Cursor, etc.):

```json
{
  "mcpServers": {
    "kgrab": {
      "command": "doc-scrape-mcp"
    }
  }
}
```

The MCP server exposes two tools:

| Tool | Description |
|------|-------------|
| `scrape_documentation` | Scrapes docs and saves `AGENTS.md` to disk |
| `scrape_documentation_to_text` | Scrapes docs and returns the markdown content directly |

---

## CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `url` | *(required)* | Entry-point URL of the documentation |
| `-o / --output` | `AGENTS.md` | Output file path |
| `-n / --name` | auto-detect | Human-friendly package name |
| `--max-pages` | 500 | Maximum pages to scrape |
| `--delay` | 0.25 | Seconds between HTTP requests |
| `-c / --compact` | off | Compress output: truncate prose, cap code, remove thin pages |
| `-v / --verbose` | off | Enable debug logging |

---

## Compact Mode

Large documentation sites can produce huge AGENTS.md files (200K+ tokens). Use `--compact` to aggressively reduce size:

| What it does | Effect |
|---|---|
| Removes thin/empty pages | Drops index and redirect pages |
| Deduplicates by title | Keeps first occurrence only |
| Strips boilerplate | Removes copyright, "Was this helpful?" etc. |
| Truncates prose | 2 sentences per section |
| Caps code blocks | 10 lines max, first block per section only |
| Cleans titles | Strips redundant site-name suffixes |

**Example:** Agno docs (500 pages) goes from **~247K tokens → ~75K tokens** (70% reduction).

---

## How It Works

1. **Crawl** — starting from the given URL, kgrab follows internal navigation links (sidebar, next/prev, etc.) and collects all reachable documentation pages under the same domain scope.
2. **Extract** — for each page it extracts headings, body text, and code examples while discarding chrome (nav, footer, scripts).
3. **Generate** — the collected content is assembled into a structured `AGENTS.md` with a table of contents, per-page sections, and inline code blocks.

---

## Development

```bash
git clone https://github.com/Bonhollow/kgrab.git
cd kgrab
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -v
```

---

## License

[Apache 2.0](LICENSE)
