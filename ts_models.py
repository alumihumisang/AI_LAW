# ts_models.py
from typing import List
import numpy as np
import requests

class EmbeddingModel:
    def __init__(self):
        self.model_name = "kenneth85/llama-3-taiwan:8b-instruct-dpo"
        self.embedding_dim = 4096
        
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        embeddings = []
        
        for text in texts:
            try:
                response = requests.post(
                    'http://localhost:11434/api/embeddings',
                    json={
                        "model": self.model_name,
                        "prompt": text
                    }
                )
                
                if response.status_code == 200:
                    embedding = response.json()['embedding']
                    embeddings.append(embedding)
                else:
                    raise Exception(f"Error getting embedding: {response.status_code}")
                    
            except Exception as e:
                print(f"Error processing text: {str(e)}")
                raise
                
        embeddings_array = np.array(embeddings)
        if embeddings_array.shape[1] != self.embedding_dim:
            raise ValueError(f"Expected embedding dimension {self.embedding_dim}, but got {embeddings_array.shape[1]}")
            
        return embeddings_array
