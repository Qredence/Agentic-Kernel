"""Tests for the CoderAgent implementation."""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from agentic_kernel.agents.coder_agent import CoderAgent


@pytest.fixture
def mock_llm():
    return Mock()


@pytest.fixture
def coder_agent(mock_llm):
    return CoderAgent(
        name="test_coder",
        description="Test coder agent",
        llm=mock_llm,
        config={
            "max_tokens": 2000,
            "temperature": 0.7,
            "supported_languages": ["python", "typescript", "javascript"]
        }
    )


async def test_coder_initialization(coder_agent):
    """Test that the coder agent is initialized correctly."""
    assert coder_agent.name == "test_coder"
    assert coder_agent.description == "Test coder agent"
    assert coder_agent.config["max_tokens"] == 2000
    assert coder_agent.config["temperature"] == 0.7
    assert "python" in coder_agent.config["supported_languages"]


async def test_code_generation(coder_agent, mock_llm):
    """Test code generation functionality."""
    mock_llm.generate_code.return_value = {
        "code": "def hello_world():\n    print('Hello, World!')",
        "language": "python",
        "explanation": "A simple hello world function"
    }
    
    result = await coder_agent.generate_code(
        "Create a hello world function",
        language="python"
    )
    
    assert "code" in result
    assert "language" in result
    assert "explanation" in result
    mock_llm.generate_code.assert_called_once()


async def test_code_review(coder_agent, mock_llm):
    """Test code review functionality."""
    code = """
    def add_numbers(a, b):
        return a + b
    """
    
    mock_llm.review_code.return_value = {
        "issues": [],
        "suggestions": ["Add type hints", "Add docstring"],
        "quality_score": 0.8
    }
    
    review = await coder_agent.review_code(code, language="python")
    
    assert "issues" in review
    assert "suggestions" in review
    assert "quality_score" in review
    mock_llm.review_code.assert_called_once_with(code, "python")


async def test_code_refactoring(coder_agent, mock_llm):
    """Test code refactoring functionality."""
    code = """
    def process_data(data):
        result = []
        for item in data:
            if item > 0:
                result.append(item * 2)
        return result
    """
    
    mock_llm.refactor_code.return_value = {
        "refactored_code": "def process_data(data):\n    return [item * 2 for item in data if item > 0]",
        "changes": ["Converted to list comprehension"],
        "improvement_metrics": {"complexity": -2, "length": -3}
    }
    
    result = await coder_agent.refactor_code(
        code,
        language="python",
        goals=["improve_readability", "reduce_complexity"]
    )
    
    assert "refactored_code" in result
    assert "changes" in result
    assert "improvement_metrics" in result
    mock_llm.refactor_code.assert_called_once()


async def test_code_explanation(coder_agent, mock_llm):
    """Test code explanation functionality."""
    code = """
    @decorator
    def complex_function(x: int) -> int:
        return x ** 2 + sum(i for i in range(x))
    """
    
    mock_llm.explain_code.return_value = {
        "explanation": "This function computes x squared plus the sum of numbers from 0 to x-1",
        "complexity_analysis": "O(n) time complexity",
        "key_concepts": ["decorators", "list comprehension", "type hints"]
    }
    
    explanation = await coder_agent.explain_code(code, language="python")
    
    assert "explanation" in explanation
    assert "complexity_analysis" in explanation
    assert "key_concepts" in explanation
    mock_llm.explain_code.assert_called_once_with(code, "python")


async def test_error_handling(coder_agent):
    """Test error handling in the coder agent."""
    # Test invalid language
    with pytest.raises(ValueError):
        await coder_agent.generate_code(
            "Create a function",
            language="invalid_lang"
        )
    
    # Test empty code
    with pytest.raises(ValueError):
        await coder_agent.review_code("", language="python")
    
    # Test missing language
    with pytest.raises(ValueError):
        await coder_agent.refactor_code("def func(): pass")


async def test_execute_task(coder_agent, mock_llm):
    """Test the execute_task method."""
    task_description = "Generate a Python function to calculate factorial"
    context = {
        "action": "generate",
        "language": "python",
        "requirements": ["must be recursive", "include type hints"]
    }
    
    mock_llm.generate_code.return_value = {
        "code": "def factorial(n: int) -> int:\n    return 1 if n <= 1 else n * factorial(n - 1)",
        "language": "python",
        "explanation": "A recursive factorial implementation"
    }
    
    result = await coder_agent.execute_task(task_description, context)
    
    assert result["status"] == "success"
    assert "output" in result
    assert "code" in result["output"]
    assert "explanation" in result["output"] 