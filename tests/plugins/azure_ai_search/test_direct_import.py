"""
Simple test file to verify that AzureAISearchPlugin can be imported.
Run with: python tests/plugins/azure_ai_search/test_direct_import.py
"""

import os
import sys

# Add src directory to path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src"))
print(f"Adding {src_path} to Python path")
sys.path.insert(0, src_path)

# Try direct imports
print("Trying direct imports...")

try:
    from agentic_kernel.plugins.azure_ai_search.azure_ai_search_plugin import AzureAISearchPlugin
    print(f"SUCCESS: AzureAISearchPlugin imported, type: {type(AzureAISearchPlugin)}")
except ImportError as e:
    print(f"ERROR: Failed to import AzureAISearchPlugin: {e}")

# Also try importlib approach
print("\nTrying importlib approach...")
import importlib.util
try:
    plugin_path = os.path.join(src_path, "agentic_kernel", "plugins", "azure_ai_search", "azure_ai_search_plugin.py")
    print(f"Looking for: {plugin_path}")
    print(f"File exists: {os.path.exists(plugin_path)}")
    
    spec = importlib.util.spec_from_file_location("azure_ai_search_plugin", plugin_path)
    if spec:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "AzureAISearchPlugin"):
            print(f"SUCCESS: AzureAISearchPlugin found via importlib")
        else:
            print(f"ERROR: Module loaded but AzureAISearchPlugin class not found")
    else:
        print(f"ERROR: Could not create spec from file")
except Exception as e:
    print(f"ERROR during importlib approach: {e}")

print("\nDone.") 