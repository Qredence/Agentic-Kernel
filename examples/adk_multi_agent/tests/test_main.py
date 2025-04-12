"""Tests for main example."""

import pytest
from examples.adk_multi_agent.main import main

@pytest.mark.asyncio
async def test_main_example():
    """Test the main example execution."""
    # Run the main example
    await main()
    
    # If we get here without exceptions, the test passes
    assert True 