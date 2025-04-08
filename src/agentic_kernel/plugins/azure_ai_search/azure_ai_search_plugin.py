import semantic_kernel as sk
from pydantic import Field
import os
import json
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ClientAuthenticationError, ServiceRequestError
import logging

logger = logging.getLogger(__name__)

class AzureAISearchPlugin:
    """Plugin to interact with Azure AI Search for vector search capabilities."""

    def __init__(self) -> None:
        """Initialize the Azure AI Search plugin using environment variables."""
        endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        key = os.getenv("AZURE_SEARCH_KEY")
        self.index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")

        if not endpoint or not key or not self.index_name:
            logger.error("Azure AI Search environment variables (ENDPOINT, KEY, INDEX_NAME) not fully set.")
            raise ValueError("Azure AI Search environment variables not set.")

        try:
            credential = AzureKeyCredential(key)
            self.search_client = SearchClient(endpoint=endpoint, index_name=self.index_name, credential=credential)
            logger.info("Azure AI Search client initialized successfully.")
        except ClientAuthenticationError:
            logger.exception("Azure AI Search authentication failed. Check your key.")
            raise
        except Exception as e:
            logger.exception(f"Failed to initialize Azure AI Search client: {e}")
            raise

    async def vector_search(
        self,
        query_vector: list[float] = Field(..., description="The vector representation of the query."),
        top_k: int = Field(default=5, description="The number of top results to retrieve."),
        vector_field_name: str = Field(default="content_vector", description="The name of the vector field in the index."),
        select_fields: list[str] | None = Field(default=None, description="List of fields to retrieve from the documents."),
        filter_expression: str | None = Field(default=None, description="OData filter expression to apply.")
    ) -> str:
        """Performs a vector search in Azure AI Search.

        Args:
            query_vector: The vector representation of the query.
            top_k: The number of top results to retrieve.
            vector_field_name: The name of the vector field in the search index.
            select_fields: Specific fields to include in the results. Defaults to all searchable fields.
            filter_expression: An OData filter expression for pre-filtering.

        Returns:
            A JSON string representing the search results, including score and selected fields.
        """
        try:
            vector_query = VectorizedQuery(vector=query_vector, k_nearest_neighbors=top_k, fields=vector_field_name)

            logger.info(f"Performing vector search on index '{self.index_name}' with top_k={top_k} on field '{vector_field_name}'. Filter: '{filter_expression}'")

            search_results = await self.search_client.search(
                search_text=None, # Use None for pure vector search
                vector_queries=[vector_query],
                select=select_fields, # Pass the select fields list
                filter=filter_expression, # Pass the filter expression
                top=top_k # Although k is in VectorizedQuery, top might also be relevant depending on API version/behavior
            )

            output_results = []
            async for result in search_results:
                doc = {field: result.get(field) for field in select_fields} if select_fields else dict(result)
                # Include the score
                doc['@search.score'] = result.get("@search.score")
                # If hybrid search is added later, vector search score might be under @search.hybrid_score
                # or within result['@search.captions'][0]['@search.score'] potentially.
                # For pure vector, @search.score should be the relevant one.
                output_results.append(doc)

            logger.info(f"Retrieved {len(output_results)} results from vector search.")
            return json.dumps(output_results)

        except ServiceRequestError as e:
            logger.error(f"Azure AI Search request failed: {e}")
            # Return empty list or re-raise depending on desired behavior
            return json.dumps([]) 
        except Exception as e:
            logger.exception(f"An unexpected error occurred during vector search: {e}")
            # Return empty list or re-raise
            return json.dumps([])

    async def close(self):
        """Close the underlying HTTP client session."""
        if hasattr(self, 'search_client') and self.search_client:
            await self.search_client.close()
            logger.info("Azure AI Search client session closed.")

# Example usage (requires environment variables to be set)
# async def main():
#     from dotenv import load_dotenv
#     load_dotenv()
#     logging.basicConfig(level=logging.INFO)

#     try:
#         plugin = AzureAISearchPlugin()
#         kernel = sk.Kernel()
#         azure_search_plugin_sk = kernel.add_plugin(plugin, "AzureSearch")
#         search_function = azure_search_plugin_sk["vector_search"]
        
#         # Replace with actual query vector from an embedding model
#         # Example: Use Azure OpenAI embeddings
#         from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, AzureTextEmbedding
#         service_id = "default"
#         embedding_gen = AzureTextEmbedding(
#             service_id=service_id,
#             api_key=os.getenv("AZURE_OPENAI_API_KEY"), 
#             endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
#             deployment_name=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME") # Ensure this env var is set
#         )
#         query_text = "What are the main benefits of using vector search?"
#         example_vector = (await embedding_gen.generate_embeddings(texts=[query_text]))[0].tolist()
#         print(f"Generated embedding for query: '{query_text}'")

#         result = await kernel.invoke(
#             search_function, 
#             query_vector=example_vector, 
#             top_k=3, 
#             select_fields=["id", "title", "chunk"], # Example fields
#             # filter_expression="category eq 'technology'" # Example filter
#         )
#         print("\nSearch Results:")
#         print(json.dumps(json.loads(result.value), indent=2))

#     except ValueError as e:
#         print(f"Initialization Error: {e}")
#     except Exception as e:
#         print(f"An error occurred: {e}")
#     finally:
#         if 'plugin' in locals() and hasattr(plugin, 'close'):
#             await plugin.close()

# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(main()) 