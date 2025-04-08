"""
Configuration file for pytest.
This file is automatically loaded by pytest at the beginning of test execution.
"""

import os
import sys
import pytest
from pathlib import Path

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Add the src directory to the Python path for all tests
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)
    print(f"Added {src_path} to Python path")

# Print some debug information to help troubleshoot import issues
print("\nPYTHON PATH:")
for p in sys.path:
    print(f"  {p}")

# Check if our module files exist
print("\nCHECKING MODULE FILES:")
module_paths = [
    os.path.join(src_path, "agentic_kernel", "plugins", "__init__.py"),
    os.path.join(src_path, "agentic_kernel", "plugins", "azure_ai_search", "__init__.py"),
    os.path.join(src_path, "agentic_kernel", "plugins", "azure_ai_search", "azure_ai_search_plugin.py"),
]
for path in module_paths:
    exists = os.path.exists(path)
    print(f"  {'✓' if exists else '✗'} {path}")

# Try importing the module directly
print("\nTRYING IMPORT:")
try:
    from agentic_kernel.plugins.azure_ai_search.azure_ai_search_plugin import AzureAISearchPlugin
    print(f"  ✓ Successfully imported AzureAISearchPlugin")
except ImportError as e:
    print(f"  ✗ Import failed: {e}")

@pytest.fixture(scope="session", autouse=True)
def setup_path():
    """Setup fixture to add the src directory to the Python path."""
    # This is intentionally empty as we already added the path above,
    # but we want to make it clear in the pytest setup that we're modifying the path
    pass 