from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import numpy as np
import hashlib
import json
import os
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

class EmbeddingModel:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', cache_dir: str = 'cache/embeddings'):
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.model = None
        self.cache = {}

        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)

        # Load model lazily
        self._load_model()

    def _load_model(self):
        """Load the sentence transformer model."""
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded embedding model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            raise

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def _load_cache(self):
        """Load embedding cache from disk."""
        cache_file = os.path.join(self.cache_dir, 'embedding_cache.json')
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    self.cache = json.load(f)
                logger.info(f"Loaded {len(self.cache)} cached embeddings")
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
                self.cache = {}

    def _save_cache(self):
        """Save embedding cache to disk."""
        cache_file = os.path.join(self.cache_dir, 'embedding_cache.json')
        try:
            with open(cache_file, 'w') as f:
                json.dump(self.cache, f)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    @lru_cache(maxsize=1000)
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text with caching."""
        cache_key = self._get_cache_key(text)

        # Check memory cache first
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Generate embedding
        if self.model is None:
            self._load_model()

        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            embedding_list = embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)

            # Cache the result
            self.cache[cache_key] = embedding_list

            # Periodically save cache to disk
            if len(self.cache) % 100 == 0:
                self._save_cache()

            return embedding_list
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 384

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts with batch processing."""
        if not texts:
            return []

        # Load cache
        self._load_cache()

        embeddings = []
        uncached_texts = []
        uncached_indices = []

        # Check cache for each text
        for i, text in enumerate(texts):
            cache_key = self._get_cache_key(text)
            if cache_key in self.cache:
                embeddings.append(self.cache[cache_key])
            else:
                embeddings.append(None)  # Placeholder
                uncached_texts.append(text)
                uncached_indices.append(i)

        # Generate embeddings for uncached texts
        if uncached_texts:
            if self.model is None:
                self._load_model()

            try:
                batch_embeddings = self.model.encode(uncached_texts, convert_to_numpy=True, batch_size=32)

                # Store in cache and fill results
                for i, (idx, embedding) in enumerate(zip(uncached_indices, batch_embeddings)):
                    embedding_list = embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
                    cache_key = self._get_cache_key(uncached_texts[i])
                    self.cache[cache_key] = embedding_list
                    embeddings[idx] = embedding_list

                logger.info(f"Generated embeddings for {len(uncached_texts)} new texts")

            except Exception as e:
                logger.error(f"Batch embedding failed: {e}")
                # Fallback to individual processing
                for i, text in zip(uncached_indices, uncached_texts):
                    embeddings[i] = self.get_embedding(text)

        # Save cache
        self._save_cache()

        return embeddings

    def get_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings."""
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

# Legacy function for backward compatibility
def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Legacy function - use EmbeddingModel class instead."""
    model = EmbeddingModel()
    return model.get_embeddings(texts)