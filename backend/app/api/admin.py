"""
Admin API endpoints for document management
"""

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import uuid

from app.services.vector_store_service import VectorStoreService
from app.utils.document_processor import DocumentProcessor

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'txt', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@admin_bp.route('/documents', methods=['GET'])
def list_documents():
    """
    List all documents in knowledge base
    GET /api/admin/documents?organization_id=demo_org
    """
    organization_id = request.args.get('organization_id', 'demo_org')
    
    try:
        vector_store = VectorStoreService(organization_id)
        documents = vector_store.list_documents()
        
        return jsonify({
            'success': True,
            'documents': documents,
            'count': len(documents)
        }), 200
        
    except Exception as e:
        print(f"Error listing documents: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'documents': []
        }), 500


@admin_bp.route('/upload-document', methods=['POST'])
def upload_document():
    """Upload document with automatic chunking for large files"""
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({
            'success': False,
            'error': f'File type not allowed. Supported: {", ".join(ALLOWED_EXTENSIONS)}'
        }), 400
    
    organization_id = request.form.get('organization_id', 'demo_org')
    category = request.form.get('category', 'general')
    
    try:
        # Create upload directory
        upload_folder = f"uploads/{organization_id}"
        os.makedirs(upload_folder, exist_ok=True)
        
        # Save file
        original_filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex[:8]}_{original_filename}"
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        print(f"✓ File saved: {file_path}")
        
        # Extract text
        processor = DocumentProcessor()
        text = processor.extract_text(file_path)
        
        if not text or len(text.strip()) < 10:
            os.remove(file_path)
            return jsonify({
                'success': False,
                'error': 'Could not extract text from document.'
            }), 400
        
        print(f"✓ Extracted {len(text)} characters")
        
        # Split into chunks if needed
        chunks = chunk_text(text, max_tokens=6000, overlap=200)
        print(f"✓ Split into {len(chunks)} chunk(s)")
        
        # Add to vector store
        vector_store = VectorStoreService(organization_id)
        document_ids = []
        
        for i, chunk in enumerate(chunks):
            chunk_metadata = {
                'filename': original_filename,
                'category': category,
                'uploaded_at': datetime.now().isoformat(),
                'file_path': file_path,
                'file_size': os.path.getsize(file_path),
                'chunk_index': i,
                'total_chunks': len(chunks),
                'is_chunked': len(chunks) > 1
            }
            
            doc_id = vector_store.add_document(
                content=chunk,
                metadata=chunk_metadata
            )
            
            document_ids.append(doc_id)
            print(f"✓ Added chunk {i+1}/{len(chunks)}: {doc_id}")
        
        return jsonify({
            'success': True,
            'document_id': document_ids[0],
            'document_ids': document_ids,
            'filename': original_filename,
            'text_length': len(text),
            'chunks': len(chunks),
            'message': f'Document uploaded successfully ({len(chunks)} chunk{"s" if len(chunks) > 1 else ""})'
        }), 200
        
    except Exception as e:
        print(f"Upload error: {e}")
        import traceback
        traceback.print_exc()
        
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/documents/<document_id>', methods=['DELETE'])
def delete_document(document_id):
    """
    Delete a document from knowledge base
    DELETE /api/admin/documents/<doc_id>?organization_id=demo_org
    """
    organization_id = request.args.get('organization_id', 'demo_org')
    
    try:
        vector_store = VectorStoreService(organization_id)
        
        # Delete from vector store
        success = vector_store.delete_document(document_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Document deleted successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Document not found'
            }), 404
            
    except Exception as e:
        print(f"Delete error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/documents/bulk-delete', methods=['POST'])
def bulk_delete_documents():
    """
    Delete multiple documents at once
    POST /api/admin/documents/bulk-delete
    Body: {
        "document_ids": ["id1", "id2", ...],
        "organization_id": "demo_org"
    }
    """
    data = request.get_json()
    document_ids = data.get('document_ids', [])
    organization_id = data.get('organization_id', 'demo_org')
    
    if not document_ids:
        return jsonify({
            'success': False,
            'error': 'No document IDs provided'
        }), 400
    
    try:
        vector_store = VectorStoreService(organization_id)
        
        deleted_count = 0
        failed_count = 0
        
        for doc_id in document_ids:
            try:
                if vector_store.delete_document(doc_id):
                    deleted_count += 1
                else:
                    failed_count += 1
            except:
                failed_count += 1
        
        return jsonify({
            'success': True,
            'deleted': deleted_count,
            'failed': failed_count,
            'message': f'Deleted {deleted_count} documents'
        }), 200
        
    except Exception as e:
        print(f"Bulk delete error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
def chunk_text(text, max_tokens=6000, overlap=200):
    """
    Split text into chunks that fit within token limits
    
    Args:
        text: Text to chunk
        max_tokens: Maximum tokens per chunk (default 6000 to be safe)
        overlap: Number of characters to overlap between chunks
    
    Returns:
        List of text chunks
    """
    # Rough estimate: 1 token ≈ 4 characters
    max_chars = max_tokens * 4
    
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        # Get chunk
        end = start + max_chars
        
        # If not at end, try to break at paragraph or sentence
        if end < len(text):
            # Look for paragraph break
            paragraph_break = text.rfind('\n\n', start, end)
            if paragraph_break > start:
                end = paragraph_break
            else:
                # Look for sentence break
                sentence_break = text.rfind('. ', start, end)
                if sentence_break > start:
                    end = sentence_break + 1
        
        chunks.append(text[start:end].strip())
        start = end - overlap  # Overlap to maintain context
    
    return chunks