#!/usr/bin/env python3
"""
Simple script to run the complex agent workflow tests.
This avoids issues with the terminal environment.
"""
import pytest
import sys
import unittest.mock

# Create a more comprehensive mock for semantic_kernel
semantic_kernel_mock = unittest.mock.MagicMock()
semantic_kernel_mock.plugin_definition = unittest.mock.MagicMock()
semantic_kernel_mock.contents = unittest.mock.MagicMock()
semantic_kernel_mock.contents.ChatHistory = unittest.mock.MagicMock()

# We need to mock modules before importing them
with unittest.mock.patch.dict('sys.modules', {
    'semantic_kernel': semantic_kernel_mock,
    'semantic_kernel.plugin_definition': semantic_kernel_mock.plugin_definition,
    'semantic_kernel.contents': semantic_kernel_mock.contents
}):
    if __name__ == "__main__":
        print("Running complex agent workflow tests...")
        # Run the specified test
        sys.exit(pytest.main([
            "tests/test_complex_agent_workflows.py::test_complex_workflow_with_multiple_dependencies",
            "-v"
        ])) 