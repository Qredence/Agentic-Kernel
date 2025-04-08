"""Vector embeddings module for memory search."""

import asyncio
from typing import List, Dict, Any
import numpy as np
from pydantic import BaseModel
import logging
from openai import AsyncAzureOpenAI

logger = logging.getLogger(__name__)


class EmbeddingConfig(BaseModel):
    """Configuration for the embedding service."""

    endpoint: str
    api_key: str
    api_version: str = "2024-02-15-preview"
    deployment_name: str = "text-embedding-3-small"
    batch_size: int = 100
    cache_embeddings: bool = True


class EmbeddingService:
    """Service for generating and managing vector embeddings."""

    def __init__(self, config: EmbeddingConfig):
        """Initialize the embedding service.

        Args:
            config: Configuration for the embedding service
        """
        self.config = config
        self._client = AsyncAzureOpenAI(
            api_key=config.api_key,
            api_version=config.api_version,
            azure_endpoint=config.endpoint,
        )
        self._cache: Dict[str, List[float]] = {}

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a list of texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        results = []
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]
            batch_results = await self._get_batch_embeddings(batch)
            results.extend(batch_results)

        return results

    async def _get_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a batch of texts.

        Args:
            texts: Batch of texts to embed

        Returns:
            List of embedding vectors
        """
        # Check cache first
        if self.config.cache_embeddings:
            cached_results = [self._cache.get(text) for text in texts]
            if all(result is not None for result in cached_results):
                return cached_results

        try:
            response = await self._client.embeddings.create(
                model=self.config.deployment_name, input=texts
            )

            embeddings = [data.embedding for data in response.data]

            # Update cache
            if self.config.cache_embeddings:
                for text, embedding in zip(texts, embeddings):
                    self._cache[text] = embedding

            return embeddings

        except Exception as e:
            logger.error(f"Error getting embeddings: {str(e)}")
            # Return zero vectors as fallback
            return [[0.0] * 1536] * len(
                texts
            )  # 1536 is the dimension for text-embedding-3-small

    def calculate_similarity(
        self, embedding1: List[float], embedding2: List[float]
    ) -> float:
        """Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score between 0 and 1
        """
        # Convert to numpy arrays for efficient computation
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def clear_cache(self):
        """Clear the embedding cache."""
        self._cache.clear()
