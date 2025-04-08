#!/usr/bin/env python
"""
Debug script to help diagnose import issues.
Run with: python debug_imports.py
"""

import sys
import os
import importlib.util

def print_separator():
    print("-" * 80)

print_separator()
print("PYTHON PATH:")
for p in sys.path:
    print(f"  {p}")
print_separator()

# Check for specific module files
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
module_paths = [
    os.path.join(src_path, "agentic_kernel", "plugins", "__init__.py"),
    os.path.join(src_path, "agentic_kernel", "plugins", "azure_ai_search", "__init__.py"),
    os.path.join(src_path, "agentic_kernel", "plugins", "azure_ai_search", "azure_ai_search_plugin.py"),
]

print("CHECKING MODULE FILES:")
for path in module_paths:
    exists = os.path.exists(path)
    print(f"  {'✓' if exists else '✗'} {path}")
print_separator()

# Try importing the module
print("TRYING IMPORT:")
sys.path.insert(0, src_path)
try:
    from agentic_kernel.plugins.azure_ai_search.azure_ai_search_plugin import AzureAISearchPlugin
    print(f"  ✓ Successfully imported AzureAISearchPlugin")
    print(f"  Module location: {AzureAISearchPlugin.__module__}")
    print(f"  Class definition: {AzureAISearchPlugin}")
except ImportError as e:
    print(f"  ✗ Import failed: {e}")
print_separator()

# Check for the presence of __pycache__ directories which might indicate Python has processed these modules
print("CHECKING __pycache__ DIRECTORIES:")
cache_paths = [
    os.path.join(src_path, "agentic_kernel", "plugins", "__pycache__"),
    os.path.join(src_path, "agentic_kernel", "plugins", "azure_ai_search", "__pycache__"),
]
for path in cache_paths:
    exists = os.path.exists(path)
    print(f"  {'✓' if exists else '✗'} {path}")
print_separator()

# Try importing directly from the file path
print("TRYING DIRECT SPEC IMPORT:")
plugin_path = os.path.join(src_path, "agentic_kernel", "plugins", "azure_ai_search", "azure_ai_search_plugin.py")
if os.path.exists(plugin_path):
    spec = importlib.util.spec_from_file_location("azure_ai_search_plugin", plugin_path)
    if spec:
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
            if hasattr(module, "AzureAISearchPlugin"):
                print(f"  ✓ Successfully loaded module directly")
                print(f"  Class found: {module.AzureAISearchPlugin}")
            else:
                print(f"  ✗ Module loaded but AzureAISearchPlugin class not found")
        except Exception as e:
            print(f"  ✗ Error loading module: {e}")
    else:
        print(f"  ✗ Could not create spec from file")
else:
    print(f"  ✗ File does not exist: {plugin_path}")
print_separator()

print("DONE") 