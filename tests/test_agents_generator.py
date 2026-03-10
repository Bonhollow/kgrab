"""Tests for doc_scraper.agents_generator module."""

from doc_scraper.scraper import PageContent, Section, ScrapeResult
from doc_scraper.agents_generator import generate_agents_md


def _make_result() -> ScrapeResult:
    """Create a small ScrapeResult fixture."""
    return ScrapeResult(
        pages=[
            PageContent(
                url="https://docs.example.com/intro",
                title="MyPkg — Introduction",
                sections=[
                    Section(
                        heading="Welcome",
                        level=1,
                        body="This is a great package.",
                        code_blocks=["pip install mypkg"],
                    ),
                ],
            ),
            PageContent(
                url="https://docs.example.com/api",
                title="MyPkg — API Reference",
                sections=[
                    Section(
                        heading="Client",
                        level=2,
                        body="Use the Client class.",
                        code_blocks=['client = Client("localhost")'],
                    ),
                    Section(heading="Server", level=2, body="Handles requests.", code_blocks=[]),
                ],
            ),
        ],
        errors={"https://docs.example.com/broken": "404 Not Found"},
    )


class TestGenerateAgentsMd:
    def test_contains_header(self):
        md = generate_agents_md(_make_result())
        assert "Agent Knowledge Base" in md

    def test_auto_detects_name(self):
        md = generate_agents_md(_make_result())
        # Should have extracted "MyPkg" from the title
        assert md.startswith("# MyPkg")

    def test_explicit_name(self):
        md = generate_agents_md(_make_result(), package_name="SuperLib")
        assert md.startswith("# SuperLib")

    def test_table_of_contents(self):
        md = generate_agents_md(_make_result())
        assert "## Table of Contents" in md
        assert "MyPkg — Introduction" in md
        assert "MyPkg — API Reference" in md

    def test_per_page_sections(self):
        md = generate_agents_md(_make_result())
        assert "## MyPkg — Introduction" in md
        assert "## MyPkg — API Reference" in md
        assert "This is a great package." in md

    def test_code_blocks_included(self):
        md = generate_agents_md(_make_result())
        assert "pip install mypkg" in md
        assert "```" in md

    def test_errors_section(self):
        md = generate_agents_md(_make_result())
        assert "could not be fetched" in md
        assert "https://docs.example.com/broken" in md

    def test_empty_result(self):
        md = generate_agents_md(ScrapeResult())
        assert "No documentation pages were found" in md
