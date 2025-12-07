"""
Services Package
----------------
This package contains all business logic services for the application.

Services:
- EmbeddingService: Generate text embeddings with OpenAI
- VectorStoreService: Store and search documents with ChromaDB  
- SentimentService: Analyze customer sentiment
- ChatService: RAG-based chatbot
- ConversationManager: Manage conversation history
"""

# Import services to make them available at package level
from .embedding_service import EmbeddingService, create_embedding_service
from .vector_store_service import VectorStoreService
from .sentiment_service import SentimentService
from .chat_service import ChatService, ConversationManager

# Define what gets imported with "from app.services import *"
__all__ = [
    'EmbeddingService',
    'create_embedding_service',
    'VectorStoreService',
    'SentimentService',
    'ChatService',
    'ConversationManager',
]

# Package metadata
__version__ = '1.0.0'
__author__ = 'AI Support SaaS'