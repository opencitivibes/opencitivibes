"""
Unit tests for HTML sanitization utilities.

Tests all XSS payloads discovered during penetration testing
to ensure they are properly neutralized.
"""

from helpers.sanitization import sanitize_html, sanitize_plain_text, sanitize_url


class TestSanitizeHtml:
    """Tests for sanitize_html function."""

    def test_removes_script_tags(self) -> None:
        """HSF-001: Classic script injection."""
        malicious = '<script>alert("XSS")</script>Safe content'
        result = sanitize_html(malicious)
        assert result is not None
        assert "<script>" not in result
        assert "</script>" not in result
        # Note: bleach strips tags but preserves text - this is safe as
        # the text is no longer executable code
        assert "Safe content" in result

    def test_removes_event_handlers(self) -> None:
        """HSF-002: Event handler-based XSS."""
        malicious = '<img src=x onerror=alert("XSS")>'
        result = sanitize_html(malicious)
        assert result is not None
        assert "onerror" not in result
        assert "<img" not in result

    def test_removes_svg_onload(self) -> None:
        """HSF-003: SVG onload XSS."""
        malicious = '<svg onload=alert("XSS")>'
        result = sanitize_html(malicious)
        assert result is not None
        assert "<svg" not in result
        assert "onload" not in result

    def test_removes_quote_breaking_xss(self) -> None:
        """HSF-004: Quote-breaking XSS."""
        malicious = '"><script>alert("XSS")</script>'
        result = sanitize_html(malicious)
        assert result is not None
        assert "<script>" not in result
        assert "</script>" not in result
        # Remaining text is safe (entities are escaped)

    def test_removes_javascript_protocol(self) -> None:
        """HSF-005: JavaScript protocol XSS in anchor tags."""
        malicious = '<a href="javascript:alert(1)">Click</a>'
        result = sanitize_html(malicious)
        assert result is not None
        assert "javascript:" not in result.lower()

    def test_preserves_allowed_tags(self) -> None:
        """Safe HTML should be preserved."""
        safe = "<p>Hello <strong>world</strong></p>"
        assert sanitize_html(safe) == safe

    def test_preserves_lists(self) -> None:
        """List elements should be preserved."""
        safe = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        assert sanitize_html(safe) == safe

    def test_preserves_formatting_tags(self) -> None:
        """Formatting tags should be preserved."""
        safe = "<p><b>bold</b> <i>italic</i> <em>emphasized</em> <u>underlined</u></p>"
        assert sanitize_html(safe) == safe

    def test_preserves_blockquote(self) -> None:
        """Blockquote should be preserved."""
        safe = "<blockquote>A famous quote</blockquote>"
        assert sanitize_html(safe) == safe

    def test_handles_none(self) -> None:
        """None input should return None."""
        assert sanitize_html(None) is None

    def test_handles_empty_string(self) -> None:
        """Empty string should return empty string."""
        assert sanitize_html("") == ""

    def test_strips_attributes_from_allowed_tags(self) -> None:
        """Attributes should be stripped even from allowed tags."""
        malicious = '<p onclick="alert(1)">Text</p>'
        result = sanitize_html(malicious)
        assert result is not None
        assert "onclick" not in result
        assert result == "<p>Text</p>"

    def test_strips_style_attributes(self) -> None:
        """Style attributes should be stripped."""
        malicious = '<p style="color:red">Styled</p>'
        result = sanitize_html(malicious)
        assert result is not None
        assert "style" not in result
        assert "<p>Styled</p>" == result

    def test_removes_iframe(self) -> None:
        """Iframes should be removed."""
        malicious = '<iframe src="http://evil.com"></iframe>'
        result = sanitize_html(malicious)
        assert result is not None
        assert "<iframe" not in result

    def test_removes_object_embed(self) -> None:
        """Object and embed tags should be removed."""
        malicious = '<object data="bad.swf"></object><embed src="bad.swf">'
        result = sanitize_html(malicious)
        assert result is not None
        assert "<object" not in result
        assert "<embed" not in result

    def test_removes_form_elements(self) -> None:
        """Form elements should be removed."""
        malicious = '<form action="http://evil.com"><input type="text"></form>'
        result = sanitize_html(malicious)
        assert result is not None
        assert "<form" not in result
        assert "<input" not in result


class TestSanitizePlainText:
    """Tests for sanitize_plain_text function."""

    def test_strips_all_html(self) -> None:
        """All HTML tags should be removed."""
        html = "<p>Hello <b>world</b></p>"
        assert sanitize_plain_text(html) == "Hello world"

    def test_strips_script_tags(self) -> None:
        """Script tags should be removed, text content is preserved (safe)."""
        malicious = "<script>alert(1)</script>Safe"
        result = sanitize_plain_text(malicious)
        assert result is not None
        assert "<script>" not in result
        assert "</script>" not in result
        assert "Safe" in result

    def test_strips_all_xss_payloads(self) -> None:
        """All XSS HTML payloads should be stripped of tags."""
        payloads = [
            '<script>alert("XSS")</script>Title',
            "<img src=x onerror=alert(1)>Title",
            "<svg onload=alert(1)>Title",
            '"><script>alert(1)</script>Title',
        ]
        for malicious in payloads:
            result = sanitize_plain_text(malicious)
            assert result is not None
            assert "<script>" not in result
            assert "<img" not in result
            assert "<svg" not in result
            assert "onerror" not in result
            assert "onload" not in result
            assert "Title" in result

    def test_handles_none(self) -> None:
        """None input should return None."""
        assert sanitize_plain_text(None) is None

    def test_handles_empty_string(self) -> None:
        """Empty string should return empty string."""
        assert sanitize_plain_text("") == ""

    def test_preserves_plain_text(self) -> None:
        """Plain text without HTML should be preserved."""
        text = "This is a simple title without HTML"
        assert sanitize_plain_text(text) == text


class TestSanitizeUrl:
    """Tests for sanitize_url function."""

    def test_blocks_javascript_protocol(self) -> None:
        """JavaScript URLs should be blocked."""
        assert sanitize_url("javascript:alert(1)") == ""
        assert sanitize_url("JAVASCRIPT:alert(1)") == ""
        assert sanitize_url("  javascript:alert(1)") == ""

    def test_blocks_javascript_with_encoding(self) -> None:
        """JavaScript with various casing should be blocked."""
        assert sanitize_url("JavaScript:alert(1)") == ""
        assert sanitize_url("JaVaScRiPt:alert(1)") == ""

    def test_allows_https(self) -> None:
        """HTTPS URLs should be allowed."""
        url = "https://example.com/page"
        assert sanitize_url(url) == url

    def test_allows_http(self) -> None:
        """HTTP URLs should be allowed."""
        url = "http://example.com/page"
        assert sanitize_url(url) == url

    def test_allows_mailto(self) -> None:
        """Mailto URLs should be allowed."""
        url = "mailto:user@example.com"
        assert sanitize_url(url) == url

    def test_allows_relative_urls_with_slash(self) -> None:
        """Relative URLs starting with slash should be allowed."""
        assert sanitize_url("/path/to/page") == "/path/to/page"
        assert sanitize_url("/api/endpoint") == "/api/endpoint"

    def test_allows_relative_urls_without_slash(self) -> None:
        """Relative URLs without slash should be allowed."""
        assert sanitize_url("page.html") == "page.html"
        assert sanitize_url("images/logo.png") == "images/logo.png"

    def test_blocks_data_protocol(self) -> None:
        """Data URLs should be blocked."""
        assert sanitize_url("data:text/html,<script>alert(1)</script>") == ""

    def test_blocks_vbscript_protocol(self) -> None:
        """VBScript URLs should be blocked."""
        assert sanitize_url("vbscript:msgbox(1)") == ""

    def test_handles_none(self) -> None:
        """None input should return None."""
        assert sanitize_url(None) is None

    def test_handles_empty_string(self) -> None:
        """Empty string should return empty string."""
        assert sanitize_url("") == ""

    def test_trims_whitespace(self) -> None:
        """Leading/trailing whitespace should be trimmed."""
        assert sanitize_url("  https://example.com  ") == "https://example.com"
