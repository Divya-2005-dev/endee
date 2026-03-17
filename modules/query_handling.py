from modules.embedding import EmbeddingModel
from typing import List, Dict, Any
import re
import logging

logger = logging.getLogger(__name__)

class QueryProcessor:
    def __init__(self, embedding_model: EmbeddingModel):
        self.embedding_model = embedding_model

    def preprocess_query(self, query: str) -> str:
        """Preprocess and clean the query."""
        # Remove extra whitespace
        query = re.sub(r'\s+', ' ', query.strip())

        # Remove special characters but keep basic punctuation
        query = re.sub(r'[^\w\s.,!?-]', '', query)

        return query

    def expand_query(self, query: str) -> List[str]:
        """Generate query variations for better retrieval."""
        variations = [query]

        # Add question variations
        if query.endswith('?'):
            # Remove question mark and add variations
            base_query = query[:-1]
            variations.extend([
                base_query,
                f"What is {base_query}",
                f"Tell me about {base_query}",
                f"Explain {base_query}"
            ])

        # Add related terms (simple keyword expansion)
        keywords = self.extract_keywords(query)
        if len(keywords) > 1:
            variations.append(' '.join(keywords))

        return list(set(variations))  # Remove duplicates

    def extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords from query."""
        # Simple keyword extraction (can be enhanced with NLP)
        words = re.findall(r'\b\w+\b', query.lower())
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'what', 'how', 'why', 'when', 'where', 'who'}

        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        return keywords[:10]  # Limit to top 10 keywords

    def process(self, query: str) -> List[float]:
        """Process query and return embedding."""
        try:
            # Preprocess
            cleaned_query = self.preprocess_query(query)

            # Get base embedding
            embedding = self.embedding_model.get_embedding(cleaned_query)

            logger.info(f"Processed query: '{query}' -> embedding of dim {len(embedding)}")
            return embedding

        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            # Return zero vector as fallback
            return [0.0] * 384

    def get_query_expansions(self, query: str, max_expansions: int = 3) -> List[str]:
        """Get query expansions for hybrid search."""
        return self.expand_query(query)[:max_expansions]

# Legacy function for backward compatibility
def process_query(query: str) -> List[float]:
    """Legacy function - use QueryProcessor class instead."""
    model = EmbeddingModel()
    processor = QueryProcessor(model)
    return processor.process(query)