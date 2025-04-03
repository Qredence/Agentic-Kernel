"""WebSurfer plugin for web search capabilities."""

import json
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl
from semantic_kernel.functions import kernel_function

class WebSearchResult(BaseModel):
    """Model for web search results."""
    title: str
    url: HttpUrl
    snippet: str
    source: str

class WebSurferPlugin:
    """Plugin for web search capabilities."""
    
    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize the WebSurfer plugin.
        
        Args:
            api_key: Optional API key for search service
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AgenticFleet/1.0 (https://github.com/AgenticFleet/agentic-kernel)'
        })

    @kernel_function(
        name="web_search",
        description="Performs a web search and returns relevant results"
    )
    def web_search(self, query: str, max_results: int = 5) -> List[WebSearchResult]:
        """Perform a web search for the given query.
        
        Args:
            query: The search query
            max_results: Maximum number of results to return (default: 5)
            
        Returns:
            List of WebSearchResult objects
        """
        # Use DuckDuckGo API for search
        search_url = "https://api.duckduckgo.com/"
        params = {
            'q': query,
            'format': 'json',
            'no_html': 1,
            'no_redirect': 1
        }
        
        try:
            response = self.session.get(search_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            # Process abstract text if available
            if data.get('AbstractText'):
                results.append(WebSearchResult(
                    title=data['AbstractSource'],
                    url=data['AbstractURL'],
                    snippet=data['AbstractText'],
                    source='DuckDuckGo Abstract'
                ))
            
            # Process related topics
            for topic in data.get('RelatedTopics', [])[:max_results - len(results)]:
                if isinstance(topic, dict) and 'Text' in topic:
                    url = topic.get('FirstURL', 'https://duckduckgo.com')
                    results.append(WebSearchResult(
                        title=topic['Text'].split(' - ')[0],
                        url=url,
                        snippet=topic['Text'],
                        source='DuckDuckGo'
                    ))
            
            return results[:max_results]
            
        except Exception as e:
            # Log error and return empty results
            print(f"Error performing web search: {e}")
            return []

    @kernel_function(
        name="summarize_webpage",
        description="Fetches and summarizes the content of a webpage"
    )
    def summarize_webpage(self, url: HttpUrl) -> str:
        """Fetch and summarize the content of a webpage.
        
        Args:
            url: The URL of the webpage to summarize
            
        Returns:
            A summary of the webpage content
        """
        try:
            # Fetch webpage content
            response = self.session.get(str(url))
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
                
            # Get text content
            text = soup.get_text()
            
            # Break into lines and remove leading/trailing space
            lines = (line.strip() for line in text.splitlines())
            
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            
            # Drop blank lines
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Create a simple summary (first 500 characters)
            summary = text[:500] + "..." if len(text) > 500 else text
            
            return summary
            
        except Exception as e:
            return f"Error summarizing webpage: {e}" 