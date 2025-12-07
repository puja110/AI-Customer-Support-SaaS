# Phase 2: Building the AI Chat Engine

## Overview
In this phase, you'll build the core AI functionality:
- Vector database setup with ChromaDB
- Document ingestion and embedding
- RAG (Retrieval Augmented Generation) implementation
- Sentiment analysis integration

**Estimated Time:** 1-2 weeks

---

## Understanding the Concepts

### What is RAG?
**Retrieval Augmented Generation** combines:
1. **Retrieval:** Finding relevant information from your knowledge base
2. **Generation:** Using that information to generate accurate responses

**Why RAG?**
- LLMs can "hallucinate" (make up information)
- RAG grounds responses in your actual documentation
- Cost-effective (only sends relevant context to LLM)

### What are Vector Embeddings?
- Numerical representations of text
- Similar meanings = similar vectors
- Enables semantic search (meaning-based, not just keyword matching)

**Example:**
```
"How do I reset my password?" 
→ [0.234, -0.123, 0.567, ...] (embedding)

"Password recovery process"
→ [0.231, -0.119, 0.571, ...] (similar vector!)
```

### What is ChromaDB?
- Open-source vector database
- Stores embeddings and metadata
- Fast similarity search

---

## Step 1: Understanding the AI Pipeline

```
User Question: "How do I reset my password?"
        ↓
    [Embedding]
        ↓
    [Vector Search in ChromaDB]
        ↓
    Retrieves: "Password Reset Guide (doc_123)"
        ↓
    [LLM with Context]
        ↓
    Response: "To reset your password, go to..."
```

---

## Step 2: Create Configuration System

### 2.1 Create config.py

Create `backend/config.py`:

```python
"""Application configuration."""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///chatbot.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # OpenAI
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = 'gpt-4-turbo-preview'  # or 'gpt-3.5-turbo' for lower cost
    OPENAI_EMBEDDING_MODEL = 'text-embedding-3-small'
    
    # ChromaDB
    CHROMA_PERSIST_DIRECTORY = os.getenv('CHROMA_PERSIST_DIRECTORY', '../data/chroma_db')
    
    # AI Settings
    MAX_CONTEXT_LENGTH = 4000  # tokens
    TEMPERATURE = 0.7  # 0 = focused, 1 = creative
    MAX_TOKENS = 500  # response length
    
    # Sentiment
    SENTIMENT_MODEL = 'distilbert-base-uncased-finetuned-sst-2-english'
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE = 20

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
```

---

## Step 3: Create Embedding Service

### 3.1 Understanding Embeddings

Create `backend/app/services/embedding_service.py`:

```python
"""Service for generating and managing embeddings."""
from openai import OpenAI
from typing import List
import numpy as np
from config import Config

class EmbeddingService:
    """Handle text embeddings using OpenAI."""
    
    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = Config.OPENAI_EMBEDDING_MODEL
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
            
        Example:
            >>> service = EmbeddingService()
            >>> embedding = service.generate_embedding("Hello world")
            >>> len(embedding)
            1536  # dimensionality of the model
        """
        try:
            # Clean the text
            text = text.replace("\n", " ").strip()
            
            if not text:
                raise ValueError("Empty text provided")
            
            # Call OpenAI API
            response = self.client.embeddings.create(
                input=[text],
                model=self.model
            )
            
            # Extract embedding
            embedding = response.data[0].embedding
            
            return embedding
            
        except Exception as e:
            print(f"Error generating embedding: {e}")
            raise
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (more efficient).
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            # Clean texts
            texts = [text.replace("\n", " ").strip() for text in texts]
            texts = [text for text in texts if text]  # Remove empty
            
            if not texts:
                return []
            
            # Call OpenAI API with batch
            response = self.client.embeddings.create(
                input=texts,
                model=self.model
            )
            
            # Extract embeddings
            embeddings = [item.embedding for item in response.data]
            
            return embeddings
            
        except Exception as e:
            print(f"Error generating batch embeddings: {e}")
            raise
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Returns value between -1 and 1:
        - 1: Identical vectors
        - 0: Orthogonal (unrelated)
        - -1: Opposite vectors
        """
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


# Test the service
if __name__ == "__main__":
    service = EmbeddingService()
    
    # Test single embedding
    text = "How do I reset my password?"
    embedding = service.generate_embedding(text)
    print(f"Generated embedding with {len(embedding)} dimensions")
    
    # Test similarity
    text1 = "password reset"
    text2 = "recover password"
    text3 = "weather forecast"
    
    emb1 = service.generate_embedding(text1)
    emb2 = service.generate_embedding(text2)
    emb3 = service.generate_embedding(text3)
    
    sim_12 = service.cosine_similarity(emb1, emb2)
    sim_13 = service.cosine_similarity(emb1, emb3)
    
    print(f"\nSimilarity between '{text1}' and '{text2}': {sim_12:.3f}")
    print(f"Similarity between '{text1}' and '{text3}': {sim_13:.3f}")
    print("\nNotice: Similar meanings have higher similarity scores!")
```

### 3.2 Test the Embedding Service

```bash
cd backend
python -m app.services.embedding_service
```

**What you'll see:**
- Embedding dimensions (1536 for text-embedding-3-small)
- High similarity (~0.8+) for related texts
- Low similarity (~0.3) for unrelated texts

---

## Step 4: Create Vector Store Service

### 4.1 ChromaDB Setup

Create `backend/app/services/vector_store_service.py`:

```python
"""Service for managing vector storage with ChromaDB."""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
from .embedding_service import EmbeddingService
from config import Config
import uuid

class VectorStoreService:
    """Manage document storage and retrieval using ChromaDB."""
    
    def __init__(self, organization_id: str):
        """
        Initialize vector store for a specific organization.
        
        Args:
            organization_id: Unique ID for the organization (multi-tenancy)
        """
        self.organization_id = organization_id
        self.embedding_service = EmbeddingService()
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=Config.CHROMA_PERSIST_DIRECTORY
        )
        
        # Create or get collection for this organization
        # Each organization gets its own collection
        collection_name = f"org_{organization_id}_docs"
        
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"organization_id": organization_id}
        )
    
    def add_document(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """
        Add a document to the vector store.
        
        Args:
            content: Document text
            metadata: Additional information (title, source, category, etc.)
            
        Returns:
            Document ID
            
        Example:
            >>> store = VectorStoreService("org_123")
            >>> doc_id = store.add_document(
            ...     content="To reset password, click Forgot Password...",
            ...     metadata={
            ...         "title": "Password Reset Guide",
            ...         "category": "account",
            ...         "source": "help_docs"
            ...     }
            ... )
        """
        try:
            # Generate unique ID
            doc_id = str(uuid.uuid4())
            
            # Generate embedding
            embedding = self.embedding_service.generate_embedding(content)
            
            # Prepare metadata
            if metadata is None:
                metadata = {}
            metadata['organization_id'] = self.organization_id
            
            # Add to collection
            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[metadata]
            )
            
            print(f"Added document {doc_id}: {metadata.get('title', 'Untitled')}")
            return doc_id
            
        except Exception as e:
            print(f"Error adding document: {e}")
            raise
    
    def add_documents_batch(self, documents: List[Dict[str, Any]]) -> List[str]:
        """
        Add multiple documents efficiently.
        
        Args:
            documents: List of dicts with 'content' and optional 'metadata'
            
        Returns:
            List of document IDs
        """
        try:
            doc_ids = [str(uuid.uuid4()) for _ in documents]
            contents = [doc['content'] for doc in documents]
            metadatas = [doc.get('metadata', {}) for doc in documents]
            
            # Add organization_id to all metadata
            for metadata in metadatas:
                metadata['organization_id'] = self.organization_id
            
            # Generate embeddings in batch (more efficient)
            embeddings = self.embedding_service.generate_embeddings_batch(contents)
            
            # Add to collection
            self.collection.add(
                ids=doc_ids,
                embeddings=embeddings,
                documents=contents,
                metadatas=metadatas
            )
            
            print(f"Added {len(doc_ids)} documents in batch")
            return doc_ids
            
        except Exception as e:
            print(f"Error adding documents batch: {e}")
            raise
    
    def search(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Search for relevant documents.
        
        Args:
            query: Search query
            n_results: Number of results to return
            
        Returns:
            List of documents with content, metadata, and similarity score
            
        Example:
            >>> results = store.search("how to reset password", n_results=3)
            >>> for result in results:
            ...     print(f"Score: {result['score']:.3f}")
            ...     print(f"Content: {result['content'][:100]}...")
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_service.generate_embedding(query)
            
            # Search in collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'score': 1 - results['distances'][0][i]  # Convert distance to similarity
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching documents: {e}")
            raise
    
    def delete_document(self, doc_id: str):
        """Delete a document from the store."""
        try:
            self.collection.delete(ids=[doc_id])
            print(f"Deleted document {doc_id}")
        except Exception as e:
            print(f"Error deleting document: {e}")
            raise
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        count = self.collection.count()
        return {
            'organization_id': self.organization_id,
            'document_count': count,
            'collection_name': self.collection.name
        }


# Test the service
if __name__ == "__main__":
    # Create test organization
    store = VectorStoreService("test_org_123")
    
    # Add sample documents
    print("Adding sample documents...\n")
    
    documents = [
        {
            "content": "To reset your password, click on 'Forgot Password' link on the login page. Enter your email address and check your inbox for reset instructions.",
            "metadata": {
                "title": "Password Reset Guide",
                "category": "account",
                "priority": "high"
            }
        },
        {
            "content": "You can update your billing information in Settings > Billing. Click 'Update Payment Method' and enter your new credit card details.",
            "metadata": {
                "title": "Update Billing Info",
                "category": "billing",
                "priority": "medium"
            }
        },
        {
            "content": "To cancel your subscription, go to Settings > Subscription and click 'Cancel Subscription'. You'll retain access until the end of your billing period.",
            "metadata": {
                "title": "Cancel Subscription",
                "category": "billing",
                "priority": "high"
            }
        },
        {
            "content": "We support integration with Slack, Microsoft Teams, and Zendesk. Visit the Integrations page to connect your tools.",
            "metadata": {
                "title": "Available Integrations",
                "category": "integrations",
                "priority": "low"
            }
        }
    ]
    
    doc_ids = store.add_documents_batch(documents)
    
    # Test search
    print("\nTesting search functionality...\n")
    
    queries = [
        "How do I change my password?",
        "I want to cancel my account",
        "What payment methods do you accept?"
    ]
    
    for query in queries:
        print(f"Query: '{query}'")
        results = store.search(query, n_results=2)
        
        for i, result in enumerate(results, 1):
            print(f"\n  Result {i} (Score: {result['score']:.3f}):")
            print(f"  Title: {result['metadata'].get('title', 'N/A')}")
            print(f"  Content: {result['content'][:80]}...")
        print("\n" + "="*80 + "\n")
    
    # Show stats
    stats = store.get_collection_stats()
    print(f"Collection Stats: {stats}")
```

### 4.2 Test Vector Store

```bash
cd backend
python -m app.services.vector_store_service
```

**What you'll observe:**
- Documents added to ChromaDB
- Semantic search finds relevant docs even with different wording
- Similarity scores showing relevance

---

## Step 5: Implement Sentiment Analysis

### 5.1 Create Sentiment Service

Create `backend/app/services/sentiment_service.py`:

```python
"""Service for analyzing customer sentiment."""
from transformers import pipeline
from typing import Dict
from config import Config

class SentimentService:
    """Analyze sentiment of customer messages."""
    
    def __init__(self):
        """Initialize sentiment analysis pipeline."""
        # Load pre-trained model
        # This model is trained on customer reviews
        self.classifier = pipeline(
            "sentiment-analysis",
            model=Config.SENTIMENT_MODEL
        )
    
    def analyze(self, text: str) -> Dict[str, any]:
        """
        Analyze sentiment of text.
        
        Args:
            text: Customer message
            
        Returns:
            Dictionary with sentiment label, score, and priority
            
        Example:
            >>> service = SentimentService()
            >>> result = service.analyze("I'm very frustrated with this issue!")
            >>> print(result)
            {
                'label': 'NEGATIVE',
                'score': 0.95,
                'priority': 'HIGH'
            }
        """
        try:
            # Run sentiment analysis
            result = self.classifier(text)[0]
            
            label = result['label']  # POSITIVE or NEGATIVE
            score = result['score']  # Confidence 0-1
            
            # Determine priority based on sentiment
            priority = self._calculate_priority(label, score)
            
            # Determine if escalation needed
            needs_escalation = self._needs_escalation(label, score, text)
            
            return {
                'label': label,
                'score': score,
                'priority': priority,
                'needs_escalation': needs_escalation,
                'raw_text': text
            }
            
        except Exception as e:
            print(f"Error analyzing sentiment: {e}")
            return {
                'label': 'NEUTRAL',
                'score': 0.5,
                'priority': 'MEDIUM',
                'needs_escalation': False,
                'error': str(e)
            }
    
    def _calculate_priority(self, label: str, score: float) -> str:
        """
        Calculate priority level.
        
        Priority Logic:
        - HIGH: Strong negative sentiment (frustrated customers)
        - MEDIUM: Weak negative or neutral
        - LOW: Positive sentiment
        """
        if label == 'NEGATIVE' and score > 0.8:
            return 'HIGH'
        elif label == 'NEGATIVE':
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _needs_escalation(self, label: str, score: float, text: str) -> bool:
        """
        Determine if message needs human escalation.
        
        Escalation triggers:
        - Very negative sentiment (score > 0.85)
        - Contains escalation keywords
        - Multiple frustration indicators
        """
        # Check sentiment
        if label == 'NEGATIVE' and score > 0.85:
            return True
        
        # Check for escalation keywords
        escalation_keywords = [
            'cancel', 'refund', 'lawsuit', 'lawyer', 'terrible',
            'worst', 'angry', 'furious', 'manager', 'supervisor',
            'unacceptable', 'disgusted', 'incompetent'
        ]
        
        text_lower = text.lower()
        for keyword in escalation_keywords:
            if keyword in text_lower:
                return True
        
        # Check for multiple frustration indicators
        frustration_words = ['frustrated', 'annoyed', 'disappointed', 'upset']
        frustration_count = sum(1 for word in frustration_words if word in text_lower)
        
        if frustration_count >= 2:
            return True
        
        return False
    
    def analyze_conversation(self, messages: list) -> Dict[str, any]:
        """
        Analyze sentiment trend over a conversation.
        
        Args:
            messages: List of message texts
            
        Returns:
            Overall sentiment analysis with trend
        """
        if not messages:
            return {'trend': 'NEUTRAL', 'scores': []}
        
        # Analyze each message
        results = [self.analyze(msg) for msg in messages]
        
        # Calculate trend
        scores = [r['score'] if r['label'] == 'POSITIVE' else -r['score'] 
                  for r in results]
        
        # Determine if sentiment is improving or declining
        if len(scores) >= 2:
            recent_avg = sum(scores[-3:]) / min(3, len(scores))
            overall_avg = sum(scores) / len(scores)
            
            if recent_avg > overall_avg + 0.2:
                trend = 'IMPROVING'
            elif recent_avg < overall_avg - 0.2:
                trend = 'DECLINING'
            else:
                trend = 'STABLE'
        else:
            trend = 'INSUFFICIENT_DATA'
        
        return {
            'trend': trend,
            'message_count': len(messages),
            'scores': scores,
            'latest_sentiment': results[-1] if results else None
        }


# Test the service
if __name__ == "__main__":
    print("Loading sentiment analysis model...")
    service = SentimentService()
    print("Model loaded!\n")
    
    # Test messages
    test_messages = [
        "Thank you so much! This really helped.",
        "I'm having some issues with my account.",
        "This is absolutely terrible! I want a refund immediately!",
        "I've been waiting for 3 days and still no response. This is unacceptable.",
        "The product works as expected.",
    ]
    
    print("Analyzing individual messages:\n")
    for msg in test_messages:
        result = service.analyze(msg)
        print(f"Message: {msg}")
        print(f"Sentiment: {result['label']} (confidence: {result['score']:.2f})")
        print(f"Priority: {result['priority']}")
        print(f"Needs Escalation: {result['needs_escalation']}")
        print("-" * 80)
    
    # Test conversation analysis
    print("\nAnalyzing conversation trend:\n")
    conversation = [
        "Hi, I have a question about billing.",
        "I was charged twice this month.",
        "This is really frustrating. Can someone help?",
        "Thank you for looking into this!",
        "Great, issue resolved!"
    ]
    
    trend_analysis = service.analyze_conversation(conversation)
    print(f"Conversation Trend: {trend_analysis['trend']}")
    print(f"Messages Analyzed: {trend_analysis['message_count']}")
    print(f"Latest Sentiment: {trend_analysis['latest_sentiment']['label']}")
```

### 5.2 Test Sentiment Service

```bash
cd backend
python -m app.services.sentiment_service
```

**First run will download the model (~250MB)**

**What you'll see:**
- Positive messages: LOW priority
- Negative messages: HIGH priority, possible escalation
- Conversation trends: IMPROVING/DECLINING/STABLE

---

## Key Learnings So Far

✓ **Embeddings**: Convert text to numerical vectors for semantic search
✓ **ChromaDB**: Store and search vectors efficiently
✓ **Sentiment Analysis**: Detect customer emotions and prioritize
✓ **Multi-tenancy**: Each organization has isolated data

---

## Next Steps

In the next document (PHASE_2_PART2.md), we'll build:
1. The RAG chain with LangChain
2. Context-aware response generation
3. Integration of all services
4. Testing the complete chat system

Would you like me to continue with Part 2 now?

---

## Testing Checklist

Before moving to Part 2, verify:
- [ ] Embedding service generates 1536-dim vectors
- [ ] Vector store can add and search documents
- [ ] Sentiment analysis correctly identifies emotions
- [ ] All services run without errors

If any issues, review the error messages and check:
1. API keys in .env file
2. Virtual environment is activated
3. All dependencies installed
