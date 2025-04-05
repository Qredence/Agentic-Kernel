"""Tests for the WebSurfer plugin."""

import pytest
import responses
from pydantic import HttpUrl

from agentic_kernel.plugins.web_surfer import WebSurferPlugin, WebSearchResult

@pytest.fixture
def web_surfer():
    """Create a WebSurfer plugin instance for testing."""
    return WebSurferPlugin()

@pytest.fixture
def mock_responses():
    """Set up mock responses for HTTP requests."""
    with responses.RequestsMock() as rsps:
        # Mock DuckDuckGo API response
        rsps.add(
            responses.GET,
            "https://api.duckduckgo.com/",
            json={
                "AbstractText": "Test abstract",
                "AbstractURL": "https://example.com/abstract",
                "AbstractSource": "Test Source",
                "RelatedTopics": [
                    {
                        "Text": "Test Topic 1 - Description",
                        "FirstURL": "https://example.com/topic1"
                    },
                    {
                        "Text": "Test Topic 2 - Description",
                        "FirstURL": "https://example.com/topic2"
                    }
                ]
            }
        )
        
        # Mock webpage content for summarization
        rsps.add(
            responses.GET,
            "https://example.com",
            body="""
            <html>
                <head><title>Test Page</title></head>
                <body>
                    <h1>Test Content</h1>
                    <p>This is a test paragraph with some content.</p>
                    <script>alert('test');</script>
                    <style>.test { color: red; }</style>
                </body>
            </html>
            """
        )
        yield rsps

def test_web_search_basic(web_surfer, mock_responses):
    """Test basic web search functionality."""
    results = web_surfer.web_search("test query")
    assert isinstance(results, list)
    assert len(results) > 0
    assert isinstance(results[0], WebSearchResult)
    assert results[0].title == "Test Source"
    assert str(results[0].url) == "https://example.com/abstract"
    assert results[0].snippet == "Test abstract"
    assert results[0].source == "DuckDuckGo Abstract"

def test_web_search_max_results(web_surfer, mock_responses):
    """Test web search with custom max_results."""
    max_results = 1
    results = web_surfer.web_search("test query", max_results=max_results)
    assert len(results) == max_results

def test_web_search_error_handling(web_surfer, mock_responses):
    """Test web search error handling."""
    # Add a failing response
    mock_responses.replace(
        responses.GET,
        "https://api.duckduckgo.com/",
        status=500
    )
    results = web_surfer.web_search("test query")
    assert isinstance(results, list)
    assert len(results) == 0

def test_summarize_webpage(web_surfer, mock_responses):
    """Test webpage summarization."""
    url = HttpUrl("https://example.com")
    summary = web_surfer.summarize_webpage(url)
    assert isinstance(summary, str)
    assert len(summary) > 0
    assert "Test Content" in summary
    assert "test paragraph" in summary
    # Check that script and style content is removed
    assert "alert('test')" not in summary
    assert ".test { color: red; }" not in summary

def test_summarize_webpage_error_handling(web_surfer, mock_responses):
    """Test webpage summarization error handling."""
    # Add a failing response
    mock_responses.replace(
        responses.GET,
        "https://example.com",
        status=404
    )
    url = HttpUrl("https://example.com")
    summary = web_surfer.summarize_webpage(url)
    assert "Error summarizing webpage" in summary

def test_web_surfer_with_api_key():
    """Test WebSurfer initialization with API key."""
    api_key = "test_key"
    plugin = WebSurferPlugin(api_key=api_key)
    assert plugin.api_key == api_key
    assert "AgenticFleet" in plugin.session.headers['User-Agent'] 