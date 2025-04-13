"""
Simplified test runner for workflow_manager tests.

This script runs the tests for the workflow_manager module without depending
on the full project infrastructure.
"""

import os
import sys

import pytest

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

if __name__ == "__main__":
    # Run the tests
    pytest.main(["-xvs", "tests/test_workflow_manager.py"])