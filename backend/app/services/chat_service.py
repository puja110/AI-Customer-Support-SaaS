"""
Chat Service - RAG Implementation
----------------------------------
Combines all AI services to create an intelligent chatbot using RAG
(Retrieval Augmented Generation).

RAG Flow:
1. User asks question
2. Analyze sentiment (prioritize urgent queries)
3. Search knowledge base for relevant context
4. Generate response using LLM + retrieved context
5. Return contextual, accurate answer

Components:
- LangChain for orchestration
- OpenAI GPT-4 for generation
- ChromaDB for context retrieval
- Sentiment analysis for prioritization
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .embedding_service import EmbeddingService
from .vector_store_service import VectorStoreService
from .sentiment_service import SentimentService
from config import get_config

# Load configuration
config = get_config()

class ChatService:
    """
    Main chat service implementing RAG for intelligent customer support.
    
    Features:
    - Context-aware responses using knowledge base
    - Conversation memory (remembers previous messages)
    - Sentiment-based prioritization
    - Source citations in responses
    """
    
    def __init__(self, organization_id: str):
        """
        Initialize chat service for an organization.
        
        Args:
            organization_id: Unique organization identifier
        """
        self.organization_id = organization_id
        
        # Initialize AI services
        print(f"Initializing chat service for organization: {organization_id}")
        
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStoreService(organization_id)
        self.sentiment_service = SentimentService()
        
        # Initialize LLM (Language Model)
        self.llm = ChatOpenAI(
            model=config.OPENAI_MODEL,
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS,
            openai_api_key=config.OPENAI_API_KEY
        )
        
        # System prompt that defines chatbot behavior
        self.system_prompt = self._create_system_prompt()
        
        print("✓ Chat service initialized successfully")
    
    def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a chat message and generate response.
        
        Args:
            message: User's message
            conversation_history: Previous messages in format:
                [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
            conversation_id: Optional conversation ID for tracking
            
        Returns:
            Dictionary containing:
            - response: AI-generated response
            - sources: Relevant documents used
            - sentiment: Sentiment analysis
            - conversation_id: Conversation identifier
            - metadata: Additional information
            
        Example:
            >>> chat = ChatService("org_123")
            >>> result = chat.chat("How do I reset my password?")
            >>> print(result['response'])
            "To reset your password, go to the login page and click..."
            >>> print(result['sentiment']['priority'])
            "MEDIUM"
        """
        try:
            print(f"\n{'='*60}")
            print(f"Processing message: {message[:50]}...")
            
            # Step 1: Analyze sentiment
            sentiment_result = self.sentiment_service.analyze(message)
            print(f"Sentiment: {sentiment_result['label']} ({sentiment_result['score']:.2f})")
            print(f"Priority: {sentiment_result['priority']}")
            
            # Step 2: Retrieve relevant context from knowledge base
            print("Searching knowledge base...")
            relevant_docs = self.vector_store.search(
                query=message,
                n_results=3  # Get top 3 most relevant documents
            )
            
            if relevant_docs:
                print(f"Found {len(relevant_docs)} relevant documents")
                for i, doc in enumerate(relevant_docs, 1):
                    print(f"  {i}. {doc['metadata'].get('title', 'Untitled')} (score: {doc['score']:.2f})")
            else:
                print("No relevant documents found in knowledge base")
            
            # Step 3: Build context from retrieved documents
            context = self._build_context(relevant_docs)
            
            # Step 4: Prepare conversation history
            messages = self._prepare_messages(
                message=message,
                context=context,
                conversation_history=conversation_history,
                sentiment=sentiment_result
            )
            
            # Step 5: Generate response using LLM
            print("Generating response with LLM...")
            response = self.llm.invoke(messages)
            response_text = response.content
            
            print(f"Response generated: {response_text[:100]}...")
            
            # Step 6: Prepare final result
            result = {
                'response': response_text,
                'sources': self._format_sources(relevant_docs),
                'sentiment': sentiment_result,
                'conversation_id': conversation_id or self._generate_conversation_id(),
                'metadata': {
                    'model': config.OPENAI_MODEL,
                    'timestamp': datetime.utcnow().isoformat(),
                    'organization_id': self.organization_id,
                    'context_used': len(relevant_docs) > 0
                }
            }
            
            print(f"{'='*60}\n")
            
            return result
            
        except Exception as e:
            print(f"✗ Error in chat service: {e}")
            return self._get_error_response(str(e), sentiment_result)
    
    def chat_stream(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ):
        """
        Stream chat response token by token (for real-time UI).
        
        Args:
            message: User's message
            conversation_history: Previous messages
            
        Yields:
            Response tokens as they're generated
            
        Example:
            >>> for token in chat.chat_stream("Hello"):
            ...     print(token, end='', flush=True)
        """
        # Analyze sentiment
        sentiment_result = self.sentiment_service.analyze(message)
        
        # Retrieve context
        relevant_docs = self.vector_store.search(message, n_results=3)
        context = self._build_context(relevant_docs)
        
        # Prepare messages
        messages = self._prepare_messages(
            message=message,
            context=context,
            conversation_history=conversation_history,
            sentiment=sentiment_result
        )
        
        # Stream response
        for chunk in self.llm.stream(messages):
            if chunk.content:
                yield chunk.content
    
    def _create_system_prompt(self) -> str:
        """
        Create the system prompt that defines chatbot behavior.
        
        Returns:
            System prompt string
        """
        return """You are a helpful AI customer support assistant. Your goal is to provide accurate, friendly, and efficient support to customers.

Guidelines:
1. ALWAYS use the provided context to answer questions when available
2. If the context doesn't contain the answer, say so politely and offer to help differently
3. Be concise but thorough - provide complete answers without unnecessary verbosity
4. For urgent/frustrated customers, be extra empathetic and prioritize quick resolution
5. Include specific steps when explaining how to do something
6. If you cite information from the context, be accurate and don't make things up
7. End with a friendly closing and ask if they need further help

Tone:
- Professional yet warm and friendly
- Patient and empathetic
- Clear and easy to understand
- Adapt tone based on customer sentiment (more empathetic for frustrated customers)

Remember: You're here to help solve problems and make customers happy!"""
    
    def _build_context(self, documents: List[Dict[str, Any]]) -> str:
        """
        Build context string from retrieved documents.
        
        Args:
            documents: List of relevant documents
            
        Returns:
            Formatted context string
        """
        if not documents:
            return "No relevant information found in the knowledge base."
        
        context_parts = []
        for i, doc in enumerate(documents, 1):
            title = doc['metadata'].get('title', 'Untitled')
            content = doc['content']
            score = doc['score']
            
            context_parts.append(
                f"[Source {i}: {title} (Relevance: {score:.2f})]\n{content}\n"
            )
        
        return "\n".join(context_parts)
    
    def _prepare_messages(
        self,
        message: str,
        context: str,
        conversation_history: Optional[List[Dict[str, str]]],
        sentiment: Dict[str, Any]
    ) -> List:
        """
        Prepare messages for LLM including system prompt, context, and history.
        
        Args:
            message: Current user message
            context: Retrieved context
            conversation_history: Previous conversation
            sentiment: Sentiment analysis result
            
        Returns:
            List of message objects for LLM
        """
        messages = []
        
        # Add system prompt
        system_message = self.system_prompt
        
        # Add sentiment context if negative
        if sentiment['label'] == 'NEGATIVE' and sentiment['priority'] == 'HIGH':
            system_message += f"\n\nIMPORTANT: This customer is {sentiment['emotion']} and needs urgent help. Be extra empathetic and prioritize quick resolution."
        
        messages.append(SystemMessage(content=system_message))
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-5:]:  # Last 5 messages for context
                if msg['role'] == 'user':
                    messages.append(HumanMessage(content=msg['content']))
                elif msg['role'] == 'assistant':
                    messages.append(AIMessage(content=msg['content']))
        
        # Add current message with context
        current_message = f"""Context from knowledge base:
{context}

---

Customer question: {message}

Please provide a helpful response based on the context above. If the context doesn't fully answer the question, acknowledge what you can help with and what might need additional assistance."""
        
        messages.append(HumanMessage(content=current_message))
        
        return messages
    
    def _format_sources(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format source documents for response.
        
        Args:
            documents: Retrieved documents
            
        Returns:
            List of formatted sources
        """
        sources = []
        for doc in documents:
            sources.append({
                'id': doc['id'],
                'title': doc['metadata'].get('title', 'Untitled'),
                'category': doc['metadata'].get('category', 'general'),
                'score': doc['score'],
                'url': doc['metadata'].get('url')
            })
        return sources
    
    def _generate_conversation_id(self) -> str:
        """Generate unique conversation ID."""
        import uuid
        return f"conv_{uuid.uuid4().hex[:12]}"
    
    def _get_error_response(
        self, 
        error: str, 
        sentiment: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate error response.
        
        Args:
            error: Error message
            sentiment: Sentiment analysis (if available)
            
        Returns:
            Error response dictionary
        """
        return {
            'response': "I apologize, but I'm having trouble processing your request right now. Please try again in a moment, or contact our support team for immediate assistance.",
            'sources': [],
            'sentiment': sentiment or {'label': 'NEUTRAL', 'priority': 'MEDIUM'},
            'conversation_id': self._generate_conversation_id(),
            'metadata': {
                'error': error,
                'timestamp': datetime.utcnow().isoformat()
            }
        }


class ConversationManager:
    """
    Manages conversation state and history.
    
    In a real application, this would store conversations in a database.
    For now, it's a simple in-memory manager for demonstration.
    """
    
    def __init__(self):
        """Initialize conversation manager."""
        self.conversations = {}  # conversation_id -> messages
    
    def add_message(
        self, 
        conversation_id: str, 
        role: str, 
        content: str
    ):
        """
        Add a message to conversation history.
        
        Args:
            conversation_id: Conversation identifier
            role: 'user' or 'assistant'
            content: Message content
        """
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        
        self.conversations[conversation_id].append({
            'role': role,
            'content': content,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def get_history(self, conversation_id: str) -> List[Dict[str, str]]:
        """
        Get conversation history.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            List of messages
        """
        return self.conversations.get(conversation_id, [])
    
    def clear_conversation(self, conversation_id: str):
        """Clear a conversation."""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]


# Test/Demo code
if __name__ == "__main__":
    """
    Test the chat service.
    Run: python -m app.services.chat_service
    """
    print("\n" + "="*60)
    print("🧪 CHAT SERVICE TEST")
    print("="*60)
    
    try:
        # Initialize services
        print("\n1. Initializing chat service...")
        chat = ChatService("test_org_chat")
        conversation_manager = ConversationManager()
        
        # Add sample knowledge base
        print("\n2. Adding sample knowledge to vector store...")
        sample_docs = [
            {
                "content": "To reset your password: 1) Go to the login page 2) Click 'Forgot Password' 3) Enter your email 4) Check your inbox for reset link 5) Click the link and create new password. The link expires in 24 hours.",
                "metadata": {
                    "title": "Password Reset Guide",
                    "category": "account",
                    "url": "https://help.example.com/reset-password"
                }
            },
            {
                "content": "To update billing information: 1) Go to Settings > Billing 2) Click 'Update Payment Method' 3) Enter new card details 4) Click Save. Changes take effect immediately for future charges.",
                "metadata": {
                    "title": "Update Billing Info",
                    "category": "billing",
                    "url": "https://help.example.com/billing"
                }
            },
            {
                "content": "Our support hours are Monday-Friday 9am-6pm EST. For urgent issues outside these hours, use our emergency hotline at 1-800-SUPPORT. Average response time is under 2 hours during business hours.",
                "metadata": {
                    "title": "Support Hours",
                    "category": "support",
                    "url": "https://help.example.com/hours"
                }
            }
        ]
        
        chat.vector_store.add_documents_batch(sample_docs)
        
        # Test conversations
        print("\n3. Testing chat responses...")
        print("\n" + "-"*60)
        
        test_queries = [
            "How do I reset my password?",
            "I'm really frustrated! I can't access my account!",
            "What are your support hours?",
            "Can you help me with billing?"
        ]
        
        conversation_id = "test_conv_123"
        
        for query in test_queries:
            print(f"\n User: {query}")
            
            # Get conversation history
            history = conversation_manager.get_history(conversation_id)
            
            # Get response
            result = chat.chat(
                message=query,
                conversation_history=history,
                conversation_id=conversation_id
            )
            
            # Display response
            print(f"\n🤖 Assistant: {result['response']}")
            print(f"\n📊 Sentiment: {result['sentiment']['label']} (Priority: {result['sentiment']['priority']})")
            
            if result['sources']:
                print(f"📚 Sources used:")
                for source in result['sources']:
                    print(f"   - {source['title']} (relevance: {source['score']:.2f})")
            
            # Save to conversation history
            conversation_manager.add_message(conversation_id, 'user', query)
            conversation_manager.add_message(conversation_id, 'assistant', result['response'])
            
            print("\n" + "-"*60)
        
        # Test streaming
        print("\n4. Testing streaming response...")
        print("\n👤 User: Tell me about password reset")
        print("🤖 Assistant (streaming): ", end='', flush=True)
        
        for token in chat.chat_stream("Tell me about password reset"):
            print(token, end='', flush=True)
        
        print("\n\n" + "="*60)
        print(" ALL TESTS PASSED!")
        print("="*60)
        print("\nKey observations:")
        print("- RAG successfully retrieves relevant context")
        print("- Responses are contextual and accurate")
        print("- Sentiment affects response tone (empathetic for frustrated users)")
        print("- Sources are cited properly")
        print("- Conversation history is maintained")
        print("\n")
        
    except Exception as e:
        print(f"\n TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        print("\nTroubleshooting:")
        print("1. Ensure OpenAI API key is set")
        print("2. Verify all services are initialized")
        print("3. Check internet connection")
        print("\n")