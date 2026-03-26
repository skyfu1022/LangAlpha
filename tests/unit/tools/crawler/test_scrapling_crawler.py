"""Unit tests for Scrapling crawler backend."""

from src.tools.crawler.backend import CrawlOutput
from src.tools.crawler.scrapling_crawler import (
    _needs_browser,
    _needs_stealth,
    _html_to_markdown,
)


class TestNeedsBrowser:
    """Tests for Tier 1 -> Tier 2 escalation detection."""

    def test_4xx_status(self):
        assert _needs_browser("<html>Access Denied</html>", 403) is True
        assert _needs_browser("<html>Not Found</html>", 404) is True

    def test_5xx_status(self):
        assert _needs_browser("<html>Server Error</html>", 500) is True

    def test_empty_body(self):
        assert _needs_browser("", 200) is True
        assert _needs_browser("   ", 200) is True

    def test_short_body(self):
        assert _needs_browser("<html><body>tiny</body></html>", 200) is True

    def test_cloudflare_signal(self):
        html = "<html><body>Just a moment... Checking your browser</body></html>" + "x" * 200
        assert _needs_browser(html, 200) is True

    def test_enable_javascript_signal(self):
        html = "<html><body>Please enable JavaScript to continue" + "x" * 200 + "</body></html>"
        assert _needs_browser(html, 200) is True

    def test_normal_page(self):
        html = "<html><body>" + "<p>Real content here.</p>" * 20 + "</body></html>"
        assert _needs_browser(html, 200) is False

    def test_case_insensitive(self):
        html = "<html><body>ACCESS DENIED" + "x" * 200 + "</body></html>"
        assert _needs_browser(html, 200) is True


class TestNeedsStealth:
    """Tests for Tier 2 -> Tier 3 escalation detection."""

    def test_403_status(self):
        assert _needs_stealth("<html>Blocked</html>", 403) is True

    def test_cloudflare_with_ray_id(self):
        html = "<html>Cloudflare challenge Ray ID: abc123</html>"
        assert _needs_stealth(html, 200) is True

    def test_cloudflare_just_a_moment(self):
        html = "<html>Cloudflare Just a moment...</html>"
        assert _needs_stealth(html, 200) is True

    def test_normal_page(self):
        html = "<html><body>Normal page content</body></html>"
        assert _needs_stealth(html, 200) is False

    def test_cloudflare_without_ray_id(self):
        # Cloudflare mention without ray id or just a moment is not stealth-needed
        html = "<html>Powered by Cloudflare</html>"
        assert _needs_stealth(html, 200) is False

    def test_401_status(self):
        assert _needs_stealth("<html>Unauthorized</html>", 401) is True

    def test_datadome_challenge(self):
        # DataDome anti-bot: short page with "enable JS" message
        html = '<html><body><p>Please enable JS and disable any ad blocker</p></body></html>'
        assert _needs_stealth(html, 200) is True

    def test_enable_js_on_large_page_not_stealth(self):
        # A large page that discusses "enable javascript" is not a challenge
        html = "<html><body>" + "x" * 3000 + "enable javascript" + "</body></html>"
        assert _needs_stealth(html, 200) is False


class TestHtmlToMarkdown:
    """Tests for HTML to markdown conversion."""

    def test_basic_conversion(self):
        html = "<h1>Title</h1><p>Paragraph text.</p>"
        md = _html_to_markdown(html)
        assert "Title" in md
        assert "Paragraph text." in md

    def test_links_preserved(self):
        html = '<a href="https://example.com">Link</a>'
        md = _html_to_markdown(html)
        assert "https://example.com" in md
        assert "Link" in md

    def test_empty_html(self):
        md = _html_to_markdown("")
        assert md.strip() == ""


class TestCrawlOutput:
    """Tests for CrawlOutput dataclass."""

    def test_create(self):
        output = CrawlOutput(title="Test", html="<p>Hi</p>", markdown="Hi")
        assert output.title == "Test"
        assert output.html == "<p>Hi</p>"
        assert output.markdown == "Hi"
