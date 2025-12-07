"""
Document Management API
-----------------------
Endpoints for managing knowledge base documents.

Endpoints:
- POST /api/documents/upload - Upload document(s)
- GET /api/documents - List all documents
- GET /api/documents/:id - Get specific document
- PUT /api/documents/:id - Update document
- DELETE /api/documents/:id - Delete document
- POST /api/documents/search - Search documents
"""

from flask import Blueprint, request, jsonify
from typing import Dict, List, Any
from datetime import datetime
import uuid

from app.services import VectorStoreService

# Create blueprint
documents_bp = Blueprint('documents', __name__, url_prefix='/api/documents')

# Store vector stores per organization
vector_stores = {}


def get_vector_store(organization_id: str) -> VectorStoreService:
    """
    Get or create vector store for organization.
    
    Args:
        organization_id: Organization identifier
        
    Returns:
        VectorStoreService instance
    """
    if organization_id not in vector_stores:
        vector_stores[organization_id] = VectorStoreService(organization_id)
    return vector_stores[organization_id]


@documents_bp.route('/upload', methods=['POST'])
def upload_document():
    """
    Upload a document to the knowledge base.
    
    Request Body:
        {
            "content": "Document text content...",
            "metadata": {
                "title": "Password Reset Guide",
                "category": "account",
                "tags": ["password", "security"],
                "url": "https://help.example.com/reset"
            },
            "organization_id": "org_123"
        }
    
    Or for batch upload:
        {
            "documents": [
                {"content": "...", "metadata": {...}},
                {"content": "...", "metadata": {...}}
            ],
            "organization_id": "org_123"
        }
    
    Response:
        {
            "message": "Document uploaded",
            "document_id": "doc_abc123",
            "organization_id": "org_123"
        }
    
    Example:
        curl -X POST http://localhost:5000/api/documents/upload \
             -H "Content-Type: application/json" \
             -d '{
                 "content": "To reset password...",
                 "metadata": {"title": "Reset Password"},
                 "organization_id": "org_123"
             }'
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        organization_id = data.get('organization_id', '').strip()
        if not organization_id:
            return jsonify({'error': 'organization_id required'}), 400
        
        # Get vector store
        store = get_vector_store(organization_id)
        
        # Check if batch upload
        if 'documents' in data:
            # Batch upload
            documents = data['documents']
            
            if not isinstance(documents, list) or len(documents) == 0:
                return jsonify({'error': 'documents must be a non-empty array'}), 400
            
            # Add documents
            doc_ids = store.add_documents_batch(documents)
            
            return jsonify({
                'message': f'Uploaded {len(doc_ids)} documents',
                'document_ids': doc_ids,
                'organization_id': organization_id,
                'count': len(doc_ids)
            }), 201
            
        else:
            # Single upload
            content = data.get('content', '').strip()
            metadata = data.get('metadata', {})
            
            if not content:
                return jsonify({'error': 'content required'}), 400
            
            # Add document
            doc_id = store.add_document(content=content, metadata=metadata)
            
            return jsonify({
                'message': 'Document uploaded',
                'document_id': doc_id,
                'organization_id': organization_id
            }), 201
            
    except Exception as e:
        print(f"Error in upload_document: {e}")
        return jsonify({'error': str(e)}), 500


@documents_bp.route('', methods=['GET'])
def list_documents():
    """
    List all documents for an organization.
    
    Query Parameters:
        organization_id: Organization ID (required)
        category: Filter by category (optional)
        limit: Max results (default: 50)
    
    Response:
        {
            "documents": [
                {
                    "id": "doc_123",
                    "metadata": {...},
                    "content_preview": "First 100 chars..."
                }
            ],
            "total": 10,
            "organization_id": "org_123"
        }
    
    Example:
        curl "http://localhost:5000/api/documents?organization_id=org_123"
    """
    try:
        organization_id = request.args.get('organization_id', '').strip()
        category = request.args.get('category', '').strip()
        limit = int(request.args.get('limit', 50))
        
        if not organization_id:
            return jsonify({'error': 'organization_id required'}), 400
        
        # Get vector store
        store = get_vector_store(organization_id)
        
        # Get stats (includes count)
        stats = store.get_stats()
        
        # Note: ChromaDB doesn't have a built-in "list all" method
        # In production, you'd store document metadata in a database
        # For now, return stats
        
        return jsonify({
            'message': 'Document list',
            'organization_id': organization_id,
            'document_count': stats['document_count'],
            'collection': stats['collection_name'],
            'note': 'Full document listing requires database integration'
        }), 200
        
    except Exception as e:
        print(f"Error in list_documents: {e}")
        return jsonify({'error': str(e)}), 500


@documents_bp.route('/<document_id>', methods=['GET'])
def get_document(document_id: str):
    """
    Get a specific document by ID.
    
    Query Parameters:
        organization_id: Organization ID (required)
    
    Response:
        {
            "id": "doc_123",
            "content": "Full document content...",
            "metadata": {...}
        }
    
    Example:
        curl "http://localhost:5000/api/documents/doc_123?organization_id=org_123"
    """
    try:
        organization_id = request.args.get('organization_id', '').strip()
        
        if not organization_id:
            return jsonify({'error': 'organization_id required'}), 400
        
        # Get vector store
        store = get_vector_store(organization_id)
        
        # Get document
        document = store.get_document(document_id)
        
        if not document:
            return jsonify({'error': 'Document not found'}), 404
        
        return jsonify(document), 200
        
    except Exception as e:
        print(f"Error in get_document: {e}")
        return jsonify({'error': str(e)}), 500


@documents_bp.route('/<document_id>', methods=['PUT'])
def update_document(document_id: str):
    """
    Update a document.
    
    Request Body:
        {
            "content": "Updated content...",  # optional
            "metadata": {...},                # optional
            "organization_id": "org_123"      # required
        }
    
    Response:
        {
            "message": "Document updated",
            "document_id": "doc_123"
        }
    
    Example:
        curl -X PUT http://localhost:5000/api/documents/doc_123 \
             -H "Content-Type: application/json" \
             -d '{"metadata": {"category": "billing"}, "organization_id": "org_123"}'
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        organization_id = data.get('organization_id', '').strip()
        if not organization_id:
            return jsonify({'error': 'organization_id required'}), 400
        
        content = data.get('content')
        metadata = data.get('metadata')
        
        if not content and not metadata:
            return jsonify({'error': 'content or metadata required'}), 400
        
        # Get vector store
        store = get_vector_store(organization_id)
        
        # Update document
        success = store.update_document(
            doc_id=document_id,
            content=content,
            metadata=metadata
        )
        
        if not success:
            return jsonify({'error': 'Document not found'}), 404
        
        return jsonify({
            'message': 'Document updated',
            'document_id': document_id
        }), 200
        
    except Exception as e:
        print(f"Error in update_document: {e}")
        return jsonify({'error': str(e)}), 500


@documents_bp.route('/<document_id>', methods=['DELETE'])
def delete_document(document_id: str):
    """
    Delete a document.
    
    Query Parameters:
        organization_id: Organization ID (required)
    
    Response:
        {
            "message": "Document deleted",
            "document_id": "doc_123"
        }
    
    Example:
        curl -X DELETE "http://localhost:5000/api/documents/doc_123?organization_id=org_123"
    """
    try:
        organization_id = request.args.get('organization_id', '').strip()
        
        if not organization_id:
            return jsonify({'error': 'organization_id required'}), 400
        
        # Get vector store
        store = get_vector_store(organization_id)
        
        # Delete document
        success = store.delete_document(document_id)
        
        if not success:
            return jsonify({'error': 'Document not found'}), 404
        
        return jsonify({
            'message': 'Document deleted',
            'document_id': document_id
        }), 200
        
    except Exception as e:
        print(f"Error in delete_document: {e}")
        return jsonify({'error': str(e)}), 500


@documents_bp.route('/search', methods=['POST'])
def search_documents():
    """
    Search documents semantically.
    
    Request Body:
        {
            "query": "password reset",
            "organization_id": "org_123",
            "n_results": 5,                    # optional, default: 5
            "filter": {"category": "account"}  # optional
        }
    
    Response:
        {
            "results": [
                {
                    "id": "doc_123",
                    "content": "...",
                    "metadata": {...},
                    "score": 0.89
                }
            ],
            "query": "password reset",
            "count": 3
        }
    
    Example:
        curl -X POST http://localhost:5000/api/documents/search \
             -H "Content-Type: application/json" \
             -d '{"query": "billing", "organization_id": "org_123"}'
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        query = data.get('query', '').strip()
        organization_id = data.get('organization_id', '').strip()
        n_results = data.get('n_results', 5)
        filter_metadata = data.get('filter')
        
        if not query:
            return jsonify({'error': 'query required'}), 400
        
        if not organization_id:
            return jsonify({'error': 'organization_id required'}), 400
        
        # Get vector store
        store = get_vector_store(organization_id)
        
        # Search
        results = store.search(
            query=query,
            n_results=n_results,
            filter_metadata=filter_metadata
        )
        
        return jsonify({
            'results': results,
            'query': query,
            'count': len(results)
        }), 200
        
    except Exception as e:
        print(f"Error in search_documents: {e}")
        return jsonify({'error': str(e)}), 500


@documents_bp.route('/stats', methods=['GET'])
def get_stats():
    """
    Get document statistics.
    
    Query Parameters:
        organization_id: Organization ID (required)
    
    Response:
        {
            "organization_id": "org_123",
            "document_count": 42,
            "collection_name": "org_123_docs"
        }
    
    Example:
        curl "http://localhost:5000/api/documents/stats?organization_id=org_123"
    """
    try:
        organization_id = request.args.get('organization_id', '').strip()
        
        if not organization_id:
            return jsonify({'error': 'organization_id required'}), 400
        
        # Get vector store
        store = get_vector_store(organization_id)
        
        # Get stats
        stats = store.get_stats()
        
        return jsonify(stats), 200
        
    except Exception as e:
        print(f"Error in get_stats: {e}")
        return jsonify({'error': str(e)}), 500


# Error handlers
@documents_bp.errorhandler(400)
def bad_request(error):
    """Handle 400 errors."""
    return jsonify({'error': 'Bad request', 'message': str(error)}), 400


@documents_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found', 'message': str(error)}), 404


@documents_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500