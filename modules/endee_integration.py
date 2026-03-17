import requests
from typing import List, Dict, Any
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class EndeeClient:
    def __init__(self, base_url: str = "http://localhost:8080", mock: bool = True):
        self.base_url = base_url
        self.mock = mock
        if mock:
            self.collections = {}  # collection_name -> {'vectors': [], 'payloads': []}

    def create_collection(self, collection_name: str, vector_dim: int):
        if self.mock:
            if collection_name not in self.collections:
                self.collections[collection_name] = {'vectors': [], 'payloads': []}
        else:
            url = f"{self.base_url}/collections"
            data = {
                "name": collection_name,
                "vector_dim": vector_dim
            }
            response = requests.post(url, json=data)
            response.raise_for_status()

    def insert_vectors(self, collection_name: str, vectors: List[List[float]], payloads: List[Dict[str, Any]]):
        if self.mock:
            if collection_name not in self.collections:
                self.create_collection(collection_name, len(vectors[0]) if vectors else 384)
            self.collections[collection_name]['vectors'].extend(vectors)
            self.collections[collection_name]['payloads'].extend(payloads)
        else:
            url = f"{self.base_url}/collections/{collection_name}/vectors"
            data = {
                "vectors": vectors,
                "payloads": payloads
            }
            response = requests.post(url, json=data)
            response.raise_for_status()

    def search(self, collection_name: str, query_vector: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        if self.mock:
            if collection_name not in self.collections:
                return []
            vectors = np.array(self.collections[collection_name]['vectors'])
            payloads = self.collections[collection_name]['payloads']
            query = np.array(query_vector).reshape(1, -1)
            similarities = cosine_similarity(query, vectors)[0]
            top_indices = np.argsort(similarities)[-limit:][::-1]
            results = []
            for idx in top_indices:
                results.append({
                    'payload': payloads[idx],
                    'score': float(similarities[idx])
                })
            return results
        else:
            url = f"{self.base_url}/collections/{collection_name}/search"
            data = {
                "vector": query_vector,
                "limit": limit
            }
            response = requests.post(url, json=data)
            response.raise_for_status()
            return response.json()