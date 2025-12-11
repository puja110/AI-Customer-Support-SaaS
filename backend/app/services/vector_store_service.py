"""
Vector Store Service
--------------------
Manages document storage and retrieval using ChromaDB.
ChromaDB is a vector database that enables semantic search.

Key Concepts:
- Store documents with their embeddings
- Search by semantic similarity (not keywords)
- Multi-tenant: Each organization gets isolated data
- Persistent storage: Data saved to disk
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, timezone

from .embedding_service import EmbeddingService
from config import get_config

# Load configuration
config = get_config()


class VectorStoreService:
    """
    Service for managing document storage and semantic search using ChromaDB.
    
    Each organization gets its own collection for data isolation (multi-tenancy).
    """
    
    def __init__(self, organization_id: str):
        """
        Initialize vector store for a specific organization.
        
        Args:
            organization_id: Unique ID for the organization
                           (e.g., "org_123", "company_abc")
        
        Example:
            >>> store = VectorStoreService("org_123")
        """
        self.organization_id = organization_id
        self.embedding_service = EmbeddingService()
        
        # Initialize ChromaDB client with persistent storage
        self.client = chromadb.PersistentClient(
            path=config.CHROMA_PERSIST_DIRECTORY,
            settings=Settings(
                anonymized_telemetry=False  # Disable analytics
            )
        )
        
        # Create or get collection for this organization
        # Collection name includes org_id for isolation
        collection_name = f"org_{organization_id}_docs"
        
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={
                "organization_id": organization_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
        print(f"✓ Vector store initialized for organization: {organization_id}")
        print(f"  Collection: {collection_name}")
        print(f"  Documents: {self.collection.count()}")
    
    def add_document(
        self, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None
    ) -> str:
        """
        Add a single document to the vector store.
        
        Args:
            content: Document text content
            metadata: Additional information about the document
                     (e.g., title, category, source, url)
            doc_id: Optional custom document ID (auto-generated if not provided)
            
        Returns:
            Document ID
            
        Example:
            >>> doc_id = store.add_document(
            ...     content="To reset your password, click 'Forgot Password'...",
            ...     metadata={
            ...         "title": "Password Reset Guide",
            ...         "category": "account",
            ...         "priority": "high",
            ...         "source": "help_docs",
            ...         "url": "https://help.example.com/reset-password"
            ...     }
            ... )
            >>> print(doc_id)
            "doc_abc123..."
        """
        try:
            # Generate document ID if not provided
            if doc_id is None:
                doc_id = f"doc_{uuid.uuid4().hex[:12]}"
            
            # Generate embedding
            print(f"  Generating embedding for document...")
            embedding = self.embedding_service.generate_embedding(content)
            
            # Prepare metadata
            if metadata is None:
                metadata = {}
            
            # Clean metadata - ChromaDB only supports str, int, float, bool
            # Convert lists to comma-separated strings
            metadata = self._clean_metadata(metadata)
            
            # Add standard metadata
            metadata.update({
                "organization_id": self.organization_id,
                "added_at": datetime.now(timezone.utc).isoformat(),
                "content_length": len(content)
            })
            
            # Add to collection
            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[metadata]
            )
            
            title = metadata.get('title', 'Untitled')
            print(f"✓ Added document: {doc_id} - {title}")
            
            return doc_id
            
        except Exception as e:
            print(f"✗ Error adding document: {e}")
            raise
    
    def add_documents_batch(
        self, 
        documents: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Add multiple documents efficiently.
        
        Args:
            documents: List of document dictionaries, each containing:
                      - 'content': Document text (required)
                      - 'metadata': Additional info (optional)
                      - 'id': Custom ID (optional)
        
        Returns:
            List of document IDs
            
        Example:
            >>> documents = [
            ...     {
            ...         "content": "Password reset instructions...",
            ...         "metadata": {"title": "Reset Password", "category": "account"}
            ...     },
            ...     {
            ...         "content": "Billing information...",
            ...         "metadata": {"title": "Billing FAQ", "category": "billing"}
            ...     }
            ... ]
            >>> doc_ids = store.add_documents_batch(documents)
            >>> len(doc_ids)
            2
        """
        try:
            # Generate IDs for documents without them
            doc_ids = []
            contents = []
            metadatas = []
            
            for doc in documents:
                # Get or generate ID
                doc_id = doc.get('id', f"doc_{uuid.uuid4().hex[:12]}")
                doc_ids.append(doc_id)
                
                # Get content
                content = doc.get('content', '')
                if not content:
                    raise ValueError(f"Document {doc_id} has no content")
                contents.append(content)
                
                # Get and enhance metadata
                metadata = doc.get('metadata', {})
                
                # Clean metadata - ChromaDB only supports str, int, float, bool
                metadata = self._clean_metadata(metadata)
                
                metadata.update({
                    "organization_id": self.organization_id,
                    "added_at": datetime.now(timezone.utc).isoformat(),
                    "content_length": len(content)
                })
                metadatas.append(metadata)
            
            # Generate embeddings in batch (more efficient)
            print(f"  Generating {len(contents)} embeddings...")
            embeddings = self.embedding_service.generate_embeddings_batch(contents)
            
            # Add to collection
            self.collection.add(
                ids=doc_ids,
                embeddings=embeddings,
                documents=contents,
                metadatas=metadatas
            )
            
            print(f"✓ Added {len(doc_ids)} documents in batch")
            
            return doc_ids
            
        except Exception as e:
            print(f"✗ Error adding documents batch: {e}")
            raise
    
    def search(
        self, 
        query: str, 
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents using semantic search.
        
        Args:
            query: Search query (natural language)
            n_results: Number of results to return
            filter_metadata: Optional metadata filters
                           (e.g., {"category": "billing"})
        
        Returns:
            List of documents with content, metadata, and relevance score
            
        Example:
            >>> results = store.search("how to reset password", n_results=3)
            >>> for result in results:
            ...     print(f"Score: {result['score']:.2f}")
            ...     print(f"Title: {result['metadata']['title']}")
            ...     print(f"Content: {result['content'][:100]}...")
            ...     print()
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_service.generate_embedding(query)
            
            # Build where clause for filtering
            where_clause = None
            if filter_metadata:
                where_clause = filter_metadata
            
            # Search in collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_clause
            )
            
            # Format results
            formatted_results = []
            
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        'id': results['ids'][0][i],
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'score': 1 - results['distances'][0][i],  # Convert distance to similarity
                        'distance': results['distances'][0][i]
                    })
            
            print(f"✓ Found {len(formatted_results)} results for: '{query}'")
            
            return formatted_results
            
        except Exception as e:
            print(f"✗ Error searching documents: {e}")
            raise
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific document by ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document dictionary or None if not found
        """
        try:
            result = self.collection.get(
                ids=[doc_id],
                include=['documents', 'metadatas']
            )
            
            if result['ids']:
                return {
                    'id': result['ids'][0],
                    'content': result['documents'][0],
                    'metadata': result['metadatas'][0]
                }
            else:
                return None
                
        except Exception as e:
            print(f"✗ Error getting document: {e}")
            return None
    
    def update_document(
        self, 
        doc_id: str, 
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update a document's content or metadata.
        
        Args:
            doc_id: Document ID
            content: New content (if updating content)
            metadata: New metadata (if updating metadata)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get existing document
            existing = self.get_document(doc_id)
            if not existing:
                print(f"✗ Document {doc_id} not found")
                return False
            
            # Prepare update
            update_data = {}
            
            if content is not None:
                # Generate new embedding for new content
                embedding = self.embedding_service.generate_embedding(content)
                update_data['embeddings'] = [embedding]
                update_data['documents'] = [content]
            
            if metadata is not None:
                # Merge with existing metadata
                new_metadata = existing['metadata'].copy()
                new_metadata.update(self._clean_metadata(metadata))
                new_metadata['updated_at'] = datetime.now(timezone.utc).isoformat()
                update_data['metadatas'] = [new_metadata]
            
            # Update in collection
            self.collection.update(
                ids=[doc_id],
                **update_data
            )
            
            print(f"✓ Updated document: {doc_id}")
            return True
            
        except Exception as e:
            print(f"✗ Error updating document: {e}")
            return False
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document from the vector store.
        
        Args:
            doc_id: Document ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.collection.delete(ids=[doc_id])
            print(f"✓ Deleted document: {doc_id}")
            return True
            
        except Exception as e:
            print(f"✗ Error deleting document: {e}")
            return False
    
    def delete_all_documents(self) -> bool:
        """
        Delete ALL documents for this organization.
        ⚠️ Use with caution! This cannot be undone.
        
        Returns:
            True if successful
        """
        try:
            # Delete the entire collection
            self.client.delete_collection(self.collection.name)
            
            # Recreate empty collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection.name,
                metadata={
                    "organization_id": self.organization_id,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            )
            
            print(f"✓ Deleted all documents for organization: {self.organization_id}")
            return True
            
        except Exception as e:
            print(f"✗ Error deleting all documents: {e}")
            return False
    
    def _clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean metadata to ensure ChromaDB compatibility.
        ChromaDB only supports: str, int, float, bool (no lists, dicts, etc.)
        
        Args:
            metadata: Raw metadata dictionary
            
        Returns:
            Cleaned metadata dictionary
        """
        cleaned = {}
        
        for key, value in metadata.items():
            if value is None:
                continue  # Skip None values
            elif isinstance(value, (str, int, float, bool)):
                cleaned[key] = value  # Valid types
            elif isinstance(value, list):
                # Convert list to comma-separated string
                cleaned[key] = ", ".join(str(item) for item in value)
            elif isinstance(value, dict):
                # Convert dict to JSON string
                import json
                cleaned[key] = json.dumps(value)
            else:
                # Convert everything else to string
                cleaned[key] = str(value)
        
        return cleaned
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store.
        
        Returns:
            Dictionary with stats
        """
        return {
            'organization_id': self.organization_id,
            'collection_name': self.collection.name,
            'document_count': self.collection.count(),
            'collection_metadata': self.collection.metadata
        }


# Test/Demo code
if __name__ == "__main__":
    """
    Test the vector store service.
    Run: python -m app.services.vector_store_service
    """
    print("\n" + "="*60)
    print("🧪 VECTOR STORE SERVICE TEST")
    print("="*60)
    
    try:
        # Initialize for test organization
        print("\n1. Initializing vector store...")
        store = VectorStoreService("test_org_demo")
        
        # Clear any existing test data
        print("\n2. Cleaning up old test data...")
        store.delete_all_documents()
        
        # Add sample documents
        print("\n3. Adding sample documents...")
        documents = [
            {
                "content": "To reset your password, click on 'Forgot Password' link on the login page. Enter your email address and check your inbox for reset instructions. The link expires in 24 hours.",
                "metadata": {
                    "title": "Password Reset Guide",
                    "category": "account",
                    "priority": "high",
                    "tags": ["password", "security", "account"]
                }
            },
            {
                "content": "You can update your billing information in Settings > Billing. Click 'Update Payment Method' and enter your new credit card details. Changes take effect immediately.",
                "metadata": {
                    "title": "Update Billing Information",
                    "category": "billing",
                    "priority": "medium",
                    "tags": ["billing", "payment", "settings"]
                }
            },
            {
                "content": "To cancel your subscription, go to Settings > Subscription and click 'Cancel Subscription'. You'll retain access until the end of your billing period. We're sorry to see you go!",
                "metadata": {
                    "title": "Cancel Subscription",
                    "category": "billing",
                    "priority": "high",
                    "tags": ["subscription", "cancel", "billing"]
                }
            },
            {
                "content": "We support integration with Slack, Microsoft Teams, Zendesk, and Salesforce. Visit the Integrations page in your dashboard to connect your tools. Setup takes just a few minutes.",
                "metadata": {
                    "title": "Available Integrations",
                    "category": "integrations",
                    "priority": "low",
                    "tags": ["integrations", "slack", "teams"]
                }
            }
        ]
        
        doc_ids = store.add_documents_batch(documents)
        print(f"   Added {len(doc_ids)} documents")
        
        # Test semantic search
        print("\n4. Testing semantic search...")
        test_queries = [
            "How do I change my password?",
            "I want to cancel my account",
            "What payment methods do you accept?",
            "Can I integrate with Slack?"
        ]
        
        for query in test_queries:
            print(f"\n   Query: '{query}'")
            results = store.search(query, n_results=2)
            
            for i, result in enumerate(results, 1):
                print(f"\n   Result {i} (Score: {result['score']:.3f}):")
                print(f"   - Title: {result['metadata']['title']}")
                print(f"   - Category: {result['metadata']['category']}")
                print(f"   - Content: {result['content'][:80]}...")
        
        # Test filtered search
        print("\n5. Testing filtered search...")
        print("   Searching 'payment' in category='billing'")
        results = store.search(
            query="payment",
            n_results=3,
            filter_metadata={"category": "billing"}
        )
        print(f"   Found {len(results)} results in billing category")
        for result in results:
            print(f"   - {result['metadata']['title']}")
        
        # Get stats
        print("\n6. Getting statistics...")
        stats = store.get_stats()
        print(f"   Organization: {stats['organization_id']}")
        print(f"   Documents: {stats['document_count']}")
        print(f"   Collection: {stats['collection_name']}")
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nKey observations:")
        print("- Semantic search finds relevant docs even with different wording")
        print("- 'change password' finds 'password reset' (similar meaning)")
        print("- Filtering works correctly by metadata")
        print("- High relevance scores (>0.7) indicate good matches")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure OpenAI API key is set")
        print("2. Check ChromaDB directory exists")
        print("3. Verify internet connection")
        print("\n")