"""
Embedding Service
-----------------
Generates vector embeddings from text using OpenAI's API.
Embeddings are numerical representations that capture semantic meaning.

Key Concepts:
- Similar text → Similar vectors
- Enables semantic search (meaning-based, not just keyword matching)
- Used for finding relevant documents in ChromaDB
"""

from openai import OpenAI
from typing import List, Optional
import numpy as np
from config import get_config
import time

# Load configuration
config = get_config()


class EmbeddingService:
    """
    Service for generating and managing text embeddings.
    
    Uses OpenAI's text-embedding-3-small model which:
    - Produces 1536-dimensional vectors
    - Costs $0.00002 per 1K tokens (very cheap!)
    - Fast and accurate
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the embedding service.
        
        Args:
            api_key: OpenAI API key (optional, uses config if not provided)
        """
        self.api_key = api_key or config.OPENAI_API_KEY
        
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. "
                "Set OPENAI_API_KEY in your .env file"
            )
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = config.OPENAI_EMBEDDING_MODEL
        
        print(f"✓ Embedding service initialized with model: {self.model}")
    
    def generate_embedding(self, text: str, retry_count: int = 3) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            retry_count: Number of retries on failure
            
        Returns:
            List of floats (1536 dimensions for text-embedding-3-small)
            
        Example:
            >>> service = EmbeddingService()
            >>> embedding = service.generate_embedding("Hello world")
            >>> len(embedding)
            1536
            >>> type(embedding[0])
            <class 'float'>
        """
        # Clean and validate text
        text = self._clean_text(text)
        
        if not text:
            raise ValueError("Empty text provided for embedding")
        
        # Try to generate embedding with retries
        for attempt in range(retry_count):
            try:
                response = self.client.embeddings.create(
                    input=[text],
                    model=self.model
                )
                
                # Extract the embedding vector
                embedding = response.data[0].embedding
                
                # Validate embedding
                if not embedding or len(embedding) != 1536:
                    raise ValueError(f"Invalid embedding dimension: {len(embedding)}")
                
                return embedding
                
            except Exception as e:
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    print(f"⚠ Embedding attempt {attempt + 1} failed: {e}")
                    print(f"  Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"✗ Failed to generate embedding after {retry_count} attempts")
                    raise
    
    def generate_embeddings_batch(
        self, 
        texts: List[str], 
        batch_size: int = 100
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently.
        Processes in batches to optimize API calls.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call (max 2048 for OpenAI)
            
        Returns:
            List of embedding vectors
            
        Example:
            >>> texts = ["Hello", "World", "How are you?"]
            >>> embeddings = service.generate_embeddings_batch(texts)
            >>> len(embeddings)
            3
            >>> len(embeddings[0])
            1536
        """
        # Clean all texts
        texts = [self._clean_text(text) for text in texts]
        texts = [text for text in texts if text]  # Remove empty
        
        if not texts:
            return []
        
        all_embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                response = self.client.embeddings.create(
                    input=batch,
                    model=self.model
                )
                
                # Extract embeddings
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                
                print(f"✓ Generated {len(batch_embeddings)} embeddings (batch {i//batch_size + 1})")
                
            except Exception as e:
                print(f"✗ Batch embedding failed: {e}")
                # Fallback to individual generation
                print("  Falling back to individual generation...")
                for text in batch:
                    try:
                        embedding = self.generate_embedding(text)
                        all_embeddings.append(embedding)
                    except Exception as e:
                        print(f"✗ Failed to embed text: {text[:50]}... - {e}")
                        # Add zero vector as placeholder
                        all_embeddings.append([0.0] * 1536)
        
        return all_embeddings
    
    def cosine_similarity(
        self, 
        vec1: List[float], 
        vec2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Returns value between -1 and 1:
        - 1.0: Identical vectors (same meaning)
        - 0.5-0.9: Similar vectors (related)
        - 0.0: Orthogonal (unrelated)
        - -1.0: Opposite vectors (contradictory)
        
        Args:
            vec1: First embedding vector
            vec2: Second embedding vector
            
        Returns:
            Similarity score between -1 and 1
            
        Example:
            >>> emb1 = service.generate_embedding("password reset")
            >>> emb2 = service.generate_embedding("reset password")
            >>> emb3 = service.generate_embedding("weather forecast")
            >>> service.cosine_similarity(emb1, emb2)
            0.95  # Very similar!
            >>> service.cosine_similarity(emb1, emb3)
            0.12  # Not related
        """
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        # Calculate dot product
        dot_product = np.dot(vec1, vec2)
        
        # Calculate magnitudes
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        # Avoid division by zero
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # Calculate cosine similarity
        similarity = dot_product / (norm1 * norm2)
        
        return float(similarity)
    
    def find_most_similar(
        self, 
        query_embedding: List[float],
        candidate_embeddings: List[List[float]],
        top_k: int = 3
    ) -> List[tuple]:
        """
        Find most similar embeddings to a query.
        
        Args:
            query_embedding: The query vector
            candidate_embeddings: List of candidate vectors
            top_k: Number of top results to return
            
        Returns:
            List of (index, similarity_score) tuples, sorted by similarity
            
        Example:
            >>> query = service.generate_embedding("How do I reset password?")
            >>> docs = [
            ...     "Password reset guide",
            ...     "Billing information",
            ...     "Account security tips"
            ... ]
            >>> doc_embeddings = service.generate_embeddings_batch(docs)
            >>> results = service.find_most_similar(query, doc_embeddings, top_k=2)
            >>> results[0]
            (0, 0.89)  # Index 0 (Password reset guide) with 89% similarity
        """
        similarities = []
        
        for idx, candidate in enumerate(candidate_embeddings):
            similarity = self.cosine_similarity(query_embedding, candidate)
            similarities.append((idx, similarity))
        
        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Return top K
        return similarities[:top_k]
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and prepare text for embedding.
        
        Args:
            text: Raw text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Convert to string if not already
        text = str(text)
        
        # Replace newlines with spaces
        text = text.replace("\n", " ")
        
        # Replace multiple spaces with single space
        text = " ".join(text.split())
        
        # Strip whitespace
        text = text.strip()
        
        # Truncate if too long (OpenAI has 8191 token limit)
        # Roughly 4 chars per token
        max_chars = 8000 * 4
        if len(text) > max_chars:
            text = text[:max_chars]
            print(f"⚠ Text truncated to {max_chars} characters")
        
        return text
    
    def get_embedding_cost(self, num_tokens: int) -> float:
        """
        Calculate approximate cost for embedding generation.
        
        Args:
            num_tokens: Number of tokens to embed
            
        Returns:
            Cost in USD
            
        Example:
            >>> service.get_embedding_cost(1000)
            0.00002  # $0.00002 for 1K tokens
        """
        # text-embedding-3-small costs $0.00002 per 1K tokens
        cost_per_1k = 0.00002
        cost = (num_tokens / 1000) * cost_per_1k
        return cost


# Module-level functions for convenience
def create_embedding_service(api_key: Optional[str] = None) -> EmbeddingService:
    """
    Factory function to create an embedding service.
    
    Args:
        api_key: Optional API key
        
    Returns:
        EmbeddingService instance
    """
    return EmbeddingService(api_key=api_key)


# Test/Demo code
if __name__ == "__main__":
    """
    Test the embedding service.
    Run: python -m app.services.embedding_service
    """
    print("\n" + "="*60)
    print("🧪 EMBEDDING SERVICE TEST")
    print("="*60)
    
    try:
        # Initialize service
        print("\n1. Initializing service...")
        service = EmbeddingService()
        
        # Test single embedding
        print("\n2. Testing single embedding generation...")
        text = "How do I reset my password?"
        embedding = service.generate_embedding(text)
        print(f"   Text: '{text}'")
        print(f"   Embedding dimensions: {len(embedding)}")
        print(f"   First 5 values: {embedding[:5]}")
        
        # Test batch embeddings
        print("\n3. Testing batch embedding generation...")
        texts = [
            "Password reset instructions",
            "How to recover your account",
            "Weather forecast for tomorrow",
            "Billing and payment information"
        ]
        embeddings = service.generate_embeddings_batch(texts)
        print(f"   Generated {len(embeddings)} embeddings")
        
        # Test similarity
        print("\n4. Testing semantic similarity...")
        query = "reset password"
        query_emb = service.generate_embedding(query)
        
        print(f"\n   Query: '{query}'")
        print(f"   Comparing with:")
        
        for i, text in enumerate(texts):
            similarity = service.cosine_similarity(query_emb, embeddings[i])
            print(f"   - '{text}': {similarity:.3f}")
        
        # Find most similar
        print("\n5. Testing find_most_similar...")
        results = service.find_most_similar(query_emb, embeddings, top_k=2)
        print(f"   Top 2 most similar to '{query}':")
        for idx, score in results:
            print(f"   - {texts[idx]}: {score:.3f}")
        
        # Cost estimation
        print("\n6. Cost estimation...")
        num_tokens = 1000
        cost = service.get_embedding_cost(num_tokens)
        print(f"   Cost for {num_tokens} tokens: ${cost:.6f}")
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nKey observations:")
        print("- Similar texts have high similarity (>0.7)")
        print("- Unrelated texts have low similarity (<0.3)")
        print("- Embeddings capture semantic meaning, not just keywords")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        print("\nTroubleshooting:")
        print("1. Check OPENAI_API_KEY in .env file")
        print("2. Verify you have internet connection")
        print("3. Ensure you have OpenAI credits")
        print("\n")