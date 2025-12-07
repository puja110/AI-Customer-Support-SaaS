"""
Chat API Endpoints
------------------
RESTful endpoints for chat operations.

Endpoints:
- POST /api/chat/message - Send message and get response
- POST /api/chat/stream - Stream response in real-time
- GET /api/chat/conversations - List all conversations
- GET /api/chat/conversations/:id - Get conversation details
- DELETE /api/chat/conversations/:id - Delete conversation
"""

from flask import Blueprint, request, jsonify, Response
from typing import Generator
import json
from datetime import datetime

from app.services import ChatService, ConversationManager

# Create blueprint
chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')

# Initialize conversation manager (in production, use database)
conversation_manager = ConversationManager()

# Store chat services per organization (in production, use proper caching)
chat_services = {}


def get_chat_service(organization_id: str) -> ChatService:
    """
    Get or create chat service for organization.
    
    Args:
        organization_id: Organization identifier
        
    Returns:
        ChatService instance
    """
    if organization_id not in chat_services:
        chat_services[organization_id] = ChatService(organization_id)
    return chat_services[organization_id]


@chat_bp.route('/message', methods=['POST'])
def send_message():
    """
    Send a message and get AI response.
    
    Request Body:
        {
            "message": "How do I reset my password?",
            "conversation_id": "conv_123",  # optional
            "organization_id": "org_123"     # required
        }
    
    Response:
        {
            "response": "To reset your password...",
            "conversation_id": "conv_123",
            "sources": [...],
            "sentiment": {...},
            "metadata": {...}
        }
    
    Example:
        curl -X POST http://localhost:5000/api/chat/message \
             -H "Content-Type: application/json" \
             -d '{"message": "Hello!", "organization_id": "org_123"}'
    """
    try:
        # Parse request
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        message = data.get('message', '').strip()
        organization_id = data.get('organization_id', '').strip()
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        if not organization_id:
            return jsonify({'error': 'Organization ID is required'}), 400
        
        # Get optional fields
        conversation_id = data.get('conversation_id')
        
        # Get chat service for this organization
        chat = get_chat_service(organization_id)
        
        # Get conversation history
        history = []
        if conversation_id:
            history = conversation_manager.get_history(conversation_id)
        
        # Generate response
        result = chat.chat(
            message=message,
            conversation_history=history,
            conversation_id=conversation_id
        )
        
        # Save to conversation history
        conv_id = result['conversation_id']
        conversation_manager.add_message(conv_id, 'user', message)
        conversation_manager.add_message(conv_id, 'assistant', result['response'])
        
        # Return response
        return jsonify(result), 200
        
    except Exception as e:
        print(f"Error in send_message: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@chat_bp.route('/stream', methods=['POST'])
def stream_message():
    """
    Stream AI response in real-time (Server-Sent Events).
    
    Request Body:
        {
            "message": "Explain quantum computing",
            "conversation_id": "conv_123",
            "organization_id": "org_123"
        }
    
    Response: Server-Sent Events stream
        data: {"token": "To", "done": false}
        data: {"token": " reset", "done": false}
        data: {"token": " your", "done": false}
        ...
        data: {"done": true, "metadata": {...}}
    
    Example:
        curl -X POST http://localhost:5000/api/chat/stream \
             -H "Content-Type: application/json" \
             -d '{"message": "Hello!", "organization_id": "org_123"}'
    """
    try:
        # Parse request
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        message = data.get('message', '').strip()
        organization_id = data.get('organization_id', '').strip()
        
        if not message or not organization_id:
            return jsonify({'error': 'Message and organization_id required'}), 400
        
        # Get optional fields
        conversation_id = data.get('conversation_id')
        
        # Get chat service
        chat = get_chat_service(organization_id)
        
        # Get history
        history = []
        if conversation_id:
            history = conversation_manager.get_history(conversation_id)
        
        def generate() -> Generator[str, None, None]:
            """Generate streaming response."""
            full_response = ""
            
            try:
                # Stream tokens
                for token in chat.chat_stream(message, history):
                    full_response += token
                    yield f"data: {json.dumps({'token': token, 'done': False})}\n\n"
                
                # Send completion
                yield f"data: {json.dumps({'done': True, 'response': full_response})}\n\n"
                
                # Save to history
                if conversation_id:
                    conversation_manager.add_message(conversation_id, 'user', message)
                    conversation_manager.add_message(conversation_id, 'assistant', full_response)
                
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
        
        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
        
    except Exception as e:
        print(f"Error in stream_message: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/conversations', methods=['GET'])
def list_conversations():
    """
    List all conversations for an organization.
    
    Query Parameters:
        organization_id: Organization identifier (required)
        limit: Number of conversations to return (default: 20)
        offset: Pagination offset (default: 0)
    
    Response:
        {
            "conversations": [
                {
                    "id": "conv_123",
                    "message_count": 5,
                    "last_message": "...",
                    "created_at": "2024-01-01T00:00:00Z"
                },
                ...
            ],
            "total": 42
        }
    
    Example:
        curl "http://localhost:5000/api/chat/conversations?organization_id=org_123"
    """
    try:
        # Get query parameters
        organization_id = request.args.get('organization_id', '').strip()
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
        
        if not organization_id:
            return jsonify({'error': 'organization_id required'}), 400
        
        # Get all conversations (filter by org in production)
        all_conversations = conversation_manager.conversations
        
        # Format response
        conversations = []
        for conv_id, messages in all_conversations.items():
            if len(messages) > 0:
                conversations.append({
                    'id': conv_id,
                    'message_count': len(messages),
                    'last_message': messages[-1]['content'][:100] if messages else '',
                    'created_at': messages[0]['timestamp'] if messages else None
                })
        
        # Sort by most recent
        conversations.sort(key=lambda x: x['created_at'] or '', reverse=True)
        
        # Paginate
        paginated = conversations[offset:offset + limit]
        
        return jsonify({
            'conversations': paginated,
            'total': len(conversations),
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        print(f"Error in list_conversations: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id: str):
    """
    Get conversation details and full message history.
    
    Path Parameters:
        conversation_id: Conversation identifier
    
    Response:
        {
            "id": "conv_123",
            "messages": [
                {
                    "role": "user",
                    "content": "Hello",
                    "timestamp": "..."
                },
                {
                    "role": "assistant",
                    "content": "Hi! How can I help?",
                    "timestamp": "..."
                }
            ],
            "message_count": 2
        }
    
    Example:
        curl http://localhost:5000/api/chat/conversations/conv_123
    """
    try:
        # Get conversation
        messages = conversation_manager.get_history(conversation_id)
        
        if not messages:
            return jsonify({'error': 'Conversation not found'}), 404
        
        return jsonify({
            'id': conversation_id,
            'messages': messages,
            'message_count': len(messages)
        }), 200
        
    except Exception as e:
        print(f"Error in get_conversation: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id: str):
    """
    Delete a conversation and all its messages.
    
    Path Parameters:
        conversation_id: Conversation identifier
    
    Response:
        {
            "message": "Conversation deleted",
            "conversation_id": "conv_123"
        }
    
    Example:
        curl -X DELETE http://localhost:5000/api/chat/conversations/conv_123
    """
    try:
        # Clear conversation
        conversation_manager.clear_conversation(conversation_id)
        
        return jsonify({
            'message': 'Conversation deleted',
            'conversation_id': conversation_id
        }), 200
        
    except Exception as e:
        print(f"Error in delete_conversation: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    
    Response:
        {
            "status": "healthy",
            "service": "chat",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    """
    return jsonify({
        'status': 'healthy',
        'service': 'chat',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


# Error handlers
@chat_bp.errorhandler(400)
def bad_request(error):
    """Handle 400 errors."""
    return jsonify({'error': 'Bad request', 'message': str(error)}), 400


@chat_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found', 'message': str(error)}), 404


@chat_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500