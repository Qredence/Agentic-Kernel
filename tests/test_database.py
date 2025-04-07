"""Tests for database operations in the application."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import chainlit as cl
from typing import List, Dict, Any
from agentic_kernel.app import list_database_tables

@pytest.fixture
def mock_neon_run_sql():
    """Mock the Neon SQL execution function."""
    with patch('mcp.functions.mcp_Neon_run_sql') as mock:
        mock.return_value = {
            "rows": [
                {"table_name": "users"},
                {"table_name": "posts"},
                {"table_name": "comments"}
            ]
        }
        yield mock

@pytest.fixture
def mock_chainlit_step():
    """Mock Chainlit Step context manager."""
    mock_step = MagicMock()
    mock_step.__aenter__ = AsyncMock()
    mock_step.__aexit__ = AsyncMock()
    mock_step.input = None
    mock_step.output = None
    
    with patch('chainlit.Step', return_value=mock_step):
        yield mock_step

@pytest.fixture
def mock_chainlit_message():
    """Mock Chainlit Message."""
    mock_msg = AsyncMock()
    mock_msg.send = AsyncMock()
    
    with patch('chainlit.Message', return_value=mock_msg):
        yield mock_msg

@pytest.mark.asyncio
async def test_list_database_tables_success(
    mock_neon_run_sql,
    mock_chainlit_step,
    mock_chainlit_message
):
    """Test successful listing of database tables."""
    # Create a mock message
    message = MagicMock()
    
    # Execute the function
    await list_database_tables(message)
    
    # Verify SQL execution
    mock_neon_run_sql.assert_called_once_with(params={
        "sql": "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';",
        "databaseName": "neondb",
        "projectId": "dark-boat-45105135"
    })
    
    # Verify output formatting
    expected_response = "Found the following tables in the database:\n\n- `users`\n- `posts`\n- `comments`\n"
    mock_chainlit_message.assert_called_once()
    mock_chainlit_message.return_value.send.assert_called_once_with(content=expected_response)

@pytest.mark.asyncio
async def test_list_database_tables_empty(
    mock_neon_run_sql,
    mock_chainlit_step,
    mock_chainlit_message
):
    """Test listing database tables when no tables exist."""
    # Mock empty result
    mock_neon_run_sql.return_value = {"rows": []}
    
    # Create a mock message
    message = MagicMock()
    
    # Execute the function
    await list_database_tables(message)
    
    # Verify output
    mock_chainlit_message.assert_called_once()
    mock_chainlit_message.return_value.send.assert_called_once_with(
        content="No tables found in the public schema."
    )

@pytest.mark.asyncio
async def test_list_database_tables_error(
    mock_neon_run_sql,
    mock_chainlit_step,
    mock_chainlit_message
):
    """Test error handling when listing database tables fails."""
    # Mock SQL execution error
    mock_neon_run_sql.side_effect = Exception("Database connection failed")
    
    # Create a mock message
    message = MagicMock()
    
    # Execute the function
    await list_database_tables(message)
    
    # Verify error handling
    mock_chainlit_message.assert_called_once()
    mock_chainlit_message.return_value.send.assert_called_once_with(
        content="Error listing database tables: Database connection failed"
    )

@pytest.mark.asyncio
async def test_list_database_tables_invalid_response(
    mock_neon_run_sql,
    mock_chainlit_step,
    mock_chainlit_message
):
    """Test handling of invalid response format."""
    # Mock invalid response format
    mock_neon_run_sql.return_value = "invalid response"
    
    # Create a mock message
    message = MagicMock()
    
    # Execute the function
    await list_database_tables(message)
    
    # Verify handling of invalid format
    mock_chainlit_message.assert_called_once()
    mock_chainlit_message.return_value.send.assert_called_once_with(
        content="No tables found or unexpected response format."
    ) 