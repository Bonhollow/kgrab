"""Tests for doc_scraper.cli module."""

import pathlib
import responses
from doc_scraper.cli import main


INDEX_HTML = """<!DOCTYPE html>
<html>
<head><title>TestPkg Docs</title></head>
<body>
<main>
  <h1>TestPkg</h1>
  <p>Welcome to the documentation.</p>
  <h2>Installation</h2>
  <p>Run pip install testpkg.</p>
  <pre><code>pip install testpkg</code></pre>
</main>
</body>
</html>"""


class TestCli:
    @responses.activate
    def test_generates_agents_md(self, tmp_path: pathlib.Path):
        url = "https://docs.testpkg.dev/intro"
        responses.add(responses.GET, url, body=INDEX_HTML, content_type="text/html")

        out_file = tmp_path / "AGENTS.md"
        main([url, "-o", str(out_file), "--delay", "0"])

        assert out_file.exists()
        content = out_file.read_text()
        assert "TestPkg" in content
        assert "pip install testpkg" in content
