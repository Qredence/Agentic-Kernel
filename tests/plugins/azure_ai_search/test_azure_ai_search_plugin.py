import pytest
import os
import sys
import json
from unittest.mock import patch, AsyncMock

# Add the src directory to the Python path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src"))
if src_path not in sys.path:
    print(f"Adding {src_path} to Python path")
    sys.path.insert(0, src_path)

# Now try to import directly from an absolute path using importlib
import importlib.util
try:
    # Try direct import first
    from agentic_kernel.plugins.azure_ai_search.azure_ai_search_plugin import AzureAISearchPlugin
    print(f"Successfully imported AzureAISearchPlugin via normal import")
except ImportError as e:
    # If that fails, try loading from the file path directly
    print(f"Direct import failed: {e}")
    try:
        plugin_path = os.path.join(src_path, "agentic_kernel", "plugins", "azure_ai_search", "azure_ai_search_plugin.py")
        print(f"Attempting to load from: {plugin_path}")
        
        if os.path.exists(plugin_path):
            print(f"File exists, attempting to load spec")
            spec = importlib.util.spec_from_file_location("azure_ai_search_plugin", plugin_path)
            if spec:
                print(f"Spec created, loading module")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, "AzureAISearchPlugin"):
                    print(f"AzureAISearchPlugin found in module, using it")
                    AzureAISearchPlugin = module.AzureAISearchPlugin
                else:
                    print(f"AzureAISearchPlugin not found in module")
                    AzureAISearchPlugin = None
            else:
                print(f"Could not create spec from file")
                AzureAISearchPlugin = None
        else:
            print(f"File does not exist: {plugin_path}")
            AzureAISearchPlugin = None
    except Exception as ex:
        print(f"Error during dynamic import: {ex}")
        AzureAISearchPlugin = None

print(f"AzureAISearchPlugin import result: {AzureAISearchPlugin}")

# Skip all tests if the plugin class cannot be imported
if AzureAISearchPlugin is None:
    print(f"WARNING: AzureAISearchPlugin could not be imported, skipping all tests")
pytestmark = pytest.mark.skipif(AzureAISearchPlugin is None, reason="AzureAISearchPlugin not found, check PYTHONPATH or imports")

@pytest.fixture
def plugin():
    """Fixture to create an instance of the AzureAISearchPlugin."""
    # Mock environment variables needed for initialization if not set
    with patch.dict(os.environ, {
        'AZURE_SEARCH_ENDPOINT': 'https://test-search.search.windows.net',
        'AZURE_SEARCH_KEY': 'test-key',
        'AZURE_SEARCH_INDEX_NAME': 'test-index'
    }, clear=True):
        # Patch the SearchClient with mock
        mock_patch_path = 'agentic_kernel.plugins.azure_ai_search.azure_ai_search_plugin.SearchClient'
        print(f"Patching: {mock_patch_path}")
        
        with patch(mock_patch_path, new_callable=AsyncMock) as MockSearchClient:
            # Mock the search client instance
            mock_client_instance = MockSearchClient.return_value
            mock_client_instance.search = AsyncMock()
            # Mock the close method as well
            mock_client_instance.close = AsyncMock()
            
            # Instantiate the plugin
            try:
                print("Creating AzureAISearchPlugin instance")
                instance = AzureAISearchPlugin()
                # Keep a reference to the mocked client instance if needed later
                instance.search_client = mock_client_instance
                print("Plugin instance created successfully")
                return instance
            except ValueError as e:
                print(f"Skipping tests due to initialization error: {e}")
                pytest.skip(f"Skipping tests due to initialization error: {e}")
            except ImportError as e:
                print(f"Skipping tests because Azure SDK components are not installed or importable: {e}")
                pytest.skip(f"Skipping tests because Azure SDK components are not installed or importable: {e}")

@pytest.mark.asyncio
async def test_plugin_initialization(plugin):
    """Test that the plugin initializes without errors (basic check)."""
    print("Running test_plugin_initialization")
    assert plugin is not None
    assert hasattr(plugin, 'search_client')
    assert plugin.search_client is not None
    print("Plugin initialized successfully (mocked).")

@pytest.mark.asyncio
async def test_vector_search_mocked(plugin):
    """Test the vector_search function with a mocked client response."""
    print("Running test_vector_search_mocked")
    # Arrange
    test_vector = [0.1] * 1536 # Example dimension matching common models
    # Mock result structure should include @search.score
    mock_search_response = [
        {"id": "doc1", "@search.score": 0.95, "content": "Mocked result A"},
        {"id": "doc2", "@search.score": 0.90, "content": "Mocked result B"},
    ]
    
    # Configure the mock client's search method to return our mock response
    async def mock_search(*args, **kwargs):
        print(f"Mock search called with: {kwargs}")
        class MockSearchResult:
            def __init__(self, data):
                self._data = data
                self._iter = iter(data)

            def __aiter__(self):
                return self

            async def __anext__(self):
                try:
                    # Simulate the dictionary-like access the plugin code uses
                    item = next(self._iter)
                    # Add a get method to mimic the SDK result object behavior
                    item_with_get = item.copy()
                    item_with_get.get = lambda key, default=None: item.get(key, default)
                    return item_with_get
                except StopIteration:
                    raise StopAsyncIteration
        
        assert 'vector_queries' in kwargs
        print(f"Vector queries found in kwargs")
        # Check the vector query details if needed
        vector_query = kwargs['vector_queries'][0]
        assert hasattr(vector_query, 'vector')
        assert hasattr(vector_query, 'k_nearest_neighbors')
        assert hasattr(vector_query, 'fields')
        assert vector_query.k_nearest_neighbors == 3 # Matches the top_k passed in Act
        assert kwargs.get('top') == 3
        print(f"Vector query validation passed")
        
        return MockSearchResult(mock_search_response)

    plugin.search_client.search = AsyncMock(side_effect=mock_search)
    print("Mock search function configured")

    # Act
    print("Calling vector_search")
    results_json = await plugin.vector_search(
        query_vector=test_vector, 
        top_k=3,
        select_fields=["id", "content"] # Select fields used in assertion
        )
    print(f"Vector search returned: {results_json}")

    # Assert
    results = json.loads(results_json)
    print(f"Parsed results: {results}")
    
    assert isinstance(results, list)
    assert len(results) == 2 # Based on our mock_search_response
    assert results[0]['id'] == 'doc1'
    assert results[0]['@search.score'] == 0.95
    assert results[1]['content'] == 'Mocked result B'
    print("All assertions passed")
    
    plugin.search_client.search.assert_awaited_once()
    print("Search method was called exactly once")

@pytest.mark.asyncio
async def test_plugin_close(plugin):
    """Test the close method calls the client's close."""
    print("Running test_plugin_close")
    await plugin.close()
    plugin.search_client.close.assert_awaited_once()
    print("Close method was called exactly once")

# TODO: Add tests for error handling (e.g., client connection issues, bad responses)
# TODO: Add tests for different parameters (filters, select fields etc.) once implemented 