"""Tests for doc_scraper.scraper module."""

import responses
from doc_scraper.scraper import (
    scrape_docs,
    _same_docs_domain,
    _should_skip,
    _extract_content,
)
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Helper HTML fixtures
# ---------------------------------------------------------------------------

INDEX_HTML = """<!DOCTYPE html>
<html>
<head><title>MyPkg - Docs</title></head>
<body>
<nav>
  <a href="/docs/getting-started">Getting Started</a>
  <a href="/docs/api-reference">API Reference</a>
</nav>
<main>
  <h1>Welcome to MyPkg</h1>
  <p>MyPkg is a great library.</p>
</main>
</body>
</html>"""

GETTING_STARTED_HTML = """<!DOCTYPE html>
<html>
<head><title>Getting Started - MyPkg</title></head>
<body>
<main>
  <h1>Getting Started</h1>
  <p>Install with pip:</p>
  <pre><code>pip install mypkg</code></pre>
  <h2>Configuration</h2>
  <p>Create a config file.</p>
</main>
</body>
</html>"""

API_REF_HTML = """<!DOCTYPE html>
<html>
<head><title>API Reference - MyPkg</title></head>
<body>
<main>
  <h1>API Reference</h1>
  <h2>Client</h2>
  <p>The Client class handles connections.</p>
  <pre><code>client = Client(host="localhost")</code></pre>
  <h2>Server</h2>
  <p>The Server class listens for requests.</p>
</main>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestSameDomain:
    def test_same_host(self):
        assert _same_docs_domain("https://docs.x.com/intro", "https://docs.x.com/guide")

    def test_different_host(self):
        assert not _same_docs_domain("https://docs.x.com/intro", "https://other.com/guide")

    def test_path_prefix(self):
        assert _same_docs_domain(
            "https://x.com/docs/intro",
            "https://x.com/docs/guide",
        )
        assert not _same_docs_domain(
            "https://x.com/docs/intro",
            "https://x.com/blog/post",
        )


class TestShouldSkip:
    def test_skip_image(self):
        assert _should_skip("https://x.com/logo.png")

    def test_skip_css(self):
        assert _should_skip("https://x.com/style.css")

    def test_allow_html(self):
        assert not _should_skip("https://x.com/docs/intro")


class TestExtractContent:
    def test_extracts_title_and_sections(self):
        soup = BeautifulSoup(GETTING_STARTED_HTML, "html.parser")
        page = _extract_content(soup, "https://example.com/docs/getting-started")
        assert page.title == "Getting Started - MyPkg"
        # Should have Introduction (implicit first) or Getting Started heading
        headings = [s.heading for s in page.sections]
        assert "Getting Started" in headings or "Introduction" in headings

    def test_extracts_code_blocks(self):
        soup = BeautifulSoup(GETTING_STARTED_HTML, "html.parser")
        page = _extract_content(soup, "https://example.com/docs/getting-started")
        all_code = []
        for s in page.sections:
            all_code.extend(s.code_blocks)
        assert any("pip install mypkg" in c for c in all_code)


# ---------------------------------------------------------------------------
# Integration test with mocked HTTP
# ---------------------------------------------------------------------------

class TestScrapeDocsIntegration:
    @responses.activate
    def test_crawls_multiple_pages(self):
        base = "https://docs.example.com/docs"
        responses.add(responses.GET, base, body=INDEX_HTML, content_type="text/html")
        responses.add(
            responses.GET,
            f"{base}/getting-started",
            body=GETTING_STARTED_HTML,
            content_type="text/html",
        )
        responses.add(
            responses.GET,
            f"{base}/api-reference",
            body=API_REF_HTML,
            content_type="text/html",
        )

        result = scrape_docs(base, delay=0, max_pages=10)
        assert len(result.pages) == 3
        titles = {p.title for p in result.pages}
        assert "MyPkg - Docs" in titles
        assert "Getting Started - MyPkg" in titles
        assert "API Reference - MyPkg" in titles
        assert len(result.errors) == 0

    @responses.activate
    def test_respects_max_pages(self):
        base = "https://docs.example.com/docs"
        responses.add(responses.GET, base, body=INDEX_HTML, content_type="text/html")
        responses.add(
            responses.GET,
            f"{base}/getting-started",
            body=GETTING_STARTED_HTML,
            content_type="text/html",
        )
        responses.add(
            responses.GET,
            f"{base}/api-reference",
            body=API_REF_HTML,
            content_type="text/html",
        )

        result = scrape_docs(base, delay=0, max_pages=2)
        assert len(result.pages) == 2

    @responses.activate
    def test_records_errors(self):
        base = "https://docs.example.com/docs"
        # Index links to a page that 404s
        html = """<html><head><title>T</title></head><body>
        <nav><a href="/docs/missing">Missing</a></nav>
        <main><p>Hi</p></main></body></html>"""
        responses.add(responses.GET, base, body=html, content_type="text/html")
        responses.add(responses.GET, f"{base}/missing", status=404)

        result = scrape_docs(base, delay=0)
        assert len(result.errors) == 1
