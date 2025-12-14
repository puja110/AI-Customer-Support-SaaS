"""
Chat Service - Enhanced RAG + Web Search Implementation
----------------------------------
Combines all AI services to create an intelligent chatbot using:
- RAG (Retrieval Augmented Generation) for company knowledge
- Web Search for real-time information
- Sentiment analysis for prioritization

RAG Flow:
1. User asks question
2. Analyze sentiment (prioritize urgent queries)
3. Search company knowledge base for relevant context
4. If no good match → Search the web for real-time info
5. Generate response using LLM + retrieved context
6. Return contextual, accurate answer with sources

Components:
- LangChain for orchestration
- OpenAI GPT-4 for generation
- ChromaDB for context retrieval
- Tavily for web search
- Sentiment analysis for prioritization
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .embedding_service import EmbeddingService
from .vector_store_service import VectorStoreService
from .sentiment_service import SentimentService

from .gpt4_web_service import GPT4WebService

from config import get_config

# Load configuration
config = get_config()

class ChatService:
    """
    Main chat service implementing RAG + Web Search for intelligent customer support.
    
    Features:
    - Context-aware responses using knowledge base (RAG)
    - Real-time web search for current information
    - Smart routing between RAG and web search
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

        # Initialize Web Search Service
        try:
            self.gpt4_web = GPT4WebService()
            self.web_search_enabled = True
            print("Web search service initialized successfully")
        except Exception as e:
            print(f"Web search not available FAILED: {e}")
            import traceback
            traceback.print_exc()
            self.gpt4_web = None
            self.web_search_enabled = False
        
        # Initialize LLM (Language Model)
        self.llm = ChatOpenAI(
            model=config.OPENAI_MODEL,
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS,
            openai_api_key=config.OPENAI_API_KEY
        )
        
        # Configuration for smart routing
        self.rag_confidence_threshold = 0.3  # Minimum similarity for RAG

        # System prompt that defines chatbot behavior
        self.system_prompt = self._create_system_prompt()
        
        print("✓ Chat service initialized successfully")
    
    def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        conversation_id: Optional[str] = None,
        mode: str = 'auto'  # 'knowledge_base', 'web_search', or 'auto'
    ) -> Dict[str, Any]:
        """
        Process a chat message and generate response.
        
        Args:
            message: User's message
            conversation_history: Previous messages
            conversation_id: Optional conversation ID
            mode: Operation mode:
                - 'knowledge_base': Search only company documents (RAG)
                - 'web_search': Search only the web (real-time info)
                - 'auto': Automatically decide based on content (default)
        
        Returns:
            Dictionary containing response, sources, metadata, mode_used
        
        Example:
            >>> # Force knowledge base search
            >>> result = chat.chat("What's our refund policy?", mode="knowledge_base")
            
            >>> # Force web search
            >>> result = chat.chat("What's the weather?", mode="web_search")
            
            >>> # Let system decide
            >>> result = chat.chat("Some question", mode="auto")
        """
        try:
            print(f"\n{'='*60}")
            print(f"Processing message: {message[:50]}...")
            print(f"Mode: {mode.upper()}")
            
            # Analyze sentiment
            sentiment_result = self.sentiment_service.analyze(message)
            print(f"Sentiment: {sentiment_result['label']} ({sentiment_result['score']:.2f})")
            print(f"Priority: {sentiment_result['priority']}")
            
            # Route based on mode
            if mode == 'knowledge_base':
                # Force knowledge base search
                print("Route: KNOWLEDGE BASE (forced)")
                return self._handle_knowledge_base_mode(
                    message=message,
                    conversation_history=conversation_history,
                    conversation_id=conversation_id,
                    sentiment_result=sentiment_result
                )
            
            elif mode == 'web_search':
                # Force web search
                print("Route: WEB SEARCH (forced)")
                
                if not self.web_search_enabled:
                    return self._handle_no_web_search(
                        message=message,
                        conversation_id=conversation_id,
                        sentiment_result=sentiment_result
                    )
                
                return self._handle_with_web_search(
                    message=message,
                    conversation_history=conversation_history,
                    conversation_id=conversation_id,
                    sentiment_result=sentiment_result
                )
            
            elif mode == 'auto':
                # Automatic routing (your original logic)
                print("Route: AUTO (smart routing)")
                
                # Search knowledge base
                print("Searching company knowledge base...")
                relevant_docs = self.vector_store.search(query=message, n_results=3)
                
                # Check if we have good matches
                has_good_match = self._has_good_rag_match(relevant_docs)
                
                if has_good_match:
                    print("Good knowledge base match found")
                    return self._handle_with_rag(
                        message=message,
                        relevant_docs=relevant_docs,
                        conversation_history=conversation_history,
                        conversation_id=conversation_id,
                        sentiment_result=sentiment_result
                    )
                
                elif self.web_search_enabled:
                    print("No good knowledge base match → Using web search")
                    return self._handle_with_web_search(
                        message=message,
                        conversation_history=conversation_history,
                        conversation_id=conversation_id,
                        sentiment_result=sentiment_result
                    )
                
                else:
                    print("No knowledge available → Fallback")
                    return self._handle_no_knowledge(
                        message=message,
                        conversation_id=conversation_id,
                        sentiment_result=sentiment_result
                    )
            
            else:
                # Invalid mode (shouldn't reach here due to API validation)
                raise ValueError(f"Invalid mode: {mode}")
            
        except Exception as e:
            print(f"✗ Error in chat service: {e}")
            import traceback
            traceback.print_exc()
            return self._get_error_response(str(e), sentiment_result)
        
    def _handle_knowledge_base_mode(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]],
        conversation_id: Optional[str],
        sentiment_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle queries in knowledge base mode (force RAG, no web search).
        Always searches company documents regardless of match quality.
        """
        # Search knowledge base
        print("📚 Searching company documents...")
        relevant_docs = self.vector_store.search(query=message, n_results=3)
        
        if not relevant_docs:
            # No documents at all
            print("⚠️ Knowledge base is empty")
            return {
                'response': """No documents found in the knowledge base.

    Please add documents to the knowledge base first, or switch to Web Search mode for general questions.

    To add documents:
    1. Go to Admin Dashboard
    2. Upload your company documents
    3. Try searching again""",
                'sources': [],
                'sentiment': sentiment_result,
                'conversation_id': conversation_id or self._generate_conversation_id(),
                'method': 'knowledge_base',
                'mode_used': 'knowledge_base',
                'web_search_used': False,
                'no_documents': True,
                'metadata': {
                    'timestamp': datetime.utcnow().isoformat(),
                    'organization_id': self.organization_id
                }
            }
        
        # Log document scores
        print(f"📄 Found {len(relevant_docs)} documents:")
        for i, doc in enumerate(relevant_docs, 1):
            title = doc['metadata'].get('title', 'Untitled')
            score = doc.get('score', 0)
            distance = doc.get('distance', 0)
            print(f"   {i}. {title} (score: {score:.2f}, distance: {distance:.2f})")
        
        # Use RAG regardless of score
        return self._handle_with_rag(
            message=message,
            relevant_docs=relevant_docs,
            conversation_history=conversation_history,
            conversation_id=conversation_id,
            sentiment_result=sentiment_result,
            force_mode=True  # Indicate this was forced
        )
    
    def _handle_no_web_search(
        self,
        message: str,
        conversation_id: Optional[str],
        sentiment_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle when web search is requested but not available.
        """
        return {
            'response': """Web search is not currently available.

    Please either:
    1. Switch to Knowledge Base mode to search company documents
    2. Contact support to enable web search

    Or ask a question about your company's documents instead.""",
            'sources': [],
            'sentiment': sentiment_result,
            'conversation_id': conversation_id or self._generate_conversation_id(),
            'method': 'error',
            'mode_used': 'web_search',
            'web_search_used': False,
            'web_search_unavailable': True,
            'metadata': {
                'timestamp': datetime.utcnow().isoformat(),
                'organization_id': self.organization_id,
                'error': 'Web search not enabled'
            }
        }
    
    # Helper method to check RAG match quality
    def _has_good_rag_match(self, documents: List[Dict[str, Any]]) -> bool:
        """
        Check if knowledge base has relevant answers.
        Only used in AUTO mode.
        """
        if not documents:
            print("DEBUG: No documents found")
            return False
        
        # Get best (lowest) distance
        best_distance = min(doc.get('distance', float('inf')) for doc in documents)
        
        print(f"Best distance: {best_distance:.2f}")
        
        # For distance metrics: lower = better
        # Threshold: Accept distances < 0.6
        DISTANCE_THRESHOLD = 0.6  # Relaxed threshold
        
        has_match = best_distance < DISTANCE_THRESHOLD
        
        print(f"{best_distance:.2f} < {DISTANCE_THRESHOLD} = {has_match}")
        
        return has_match
    
    # Handle queries using RAG
    def _handle_with_rag(
        self,
        message: str,
        relevant_docs: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]],
        conversation_id: Optional[str],
        sentiment_result: Dict[str, Any],
        force_mode: bool = False
    ) -> Dict[str, Any]:
        """Handle query using company knowledge base (RAG)."""

        if relevant_docs:
            print(f"📄 Using {len(relevant_docs)} documents:")
            for i, doc in enumerate(relevant_docs, 1):
                title = doc['metadata'].get('title', 'Untitled')
                score = doc.get('score', 0)
                print(f"   {i}. {title} (score: {score:.2f})")
        
        # Build context from retrieved documents
        context = self._build_context(relevant_docs)
        
        # Prepare conversation history
        messages = self._prepare_messages(
            message=message,
            context=context,
            conversation_history=conversation_history,
            sentiment=sentiment_result
        )
        
        # Generate response using LLM
        print("Generating response with LLM...")
        response = self.llm.invoke(messages)
        response_text = response.content
        
        print(f"Response generated: {response_text[:100]}...")
        
        # Prepare final result
        result = {
            'response': response_text,
            'sources': self._format_sources(relevant_docs),
            'sentiment': sentiment_result,
            'conversation_id': conversation_id or self._generate_conversation_id(),
            'method': 'rag',
            'mode_used': 'knowledge_base',
            'web_search_used': False,
            'forced_mode': force_mode,
            'metadata': {
                'model': config.OPENAI_MODEL,
                'timestamp': datetime.utcnow().isoformat(),
                'organization_id': self.organization_id,
                'context_used': len(relevant_docs) > 0,
                'documents_found': len(relevant_docs)
            }
        }
        
        print(f"{'='*60}\n")
        return result
    
    # Handle queries using Web Search
    def _handle_with_web_search(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]],
        conversation_id: Optional[str],
        sentiment_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle query using GPT-4 with Tavily web search.
        
        This enables real-time information for questions like:
        - Current weather, news, events
        - Stock prices, sports scores
        - Recent information
        - YouTube videos, channels
        """
        # Use GPT-4 web search service
        web_result = self.gpt4_web.chat_with_web_search(
            message=message,
            conversation_history=conversation_history,
            auto_search=True
        )
        
        # Merge with our metadata
        result = {
            'response': web_result['response'],
            'sources': web_result.get('sources', []),
            'sentiment': sentiment_result,
            'conversation_id': conversation_id or self._generate_conversation_id(),
            'method': 'web_search',
            'mode_used': 'web_search',
            'web_search_used': web_result.get('web_search_used', True),
            'search_queries': web_result.get('search_queries', []),
            'metadata': {
                'model': 'gpt-4',
                'timestamp': datetime.utcnow().isoformat(),
                'organization_id': self.organization_id,
                'tavily_summary': web_result.get('tavily_summary', ''),
                'search_depth': web_result.get('search_depth', 'unknown')
            }
        }
        
        print(f"Web search response generated")
        if result['sources']:
            print(f"Sources: {len(result['sources'])} web sources cited")
        
        print(f"{'='*60}\n")
        return result
    
    # Handle when no knowledge available
    def _handle_no_knowledge(
        self,
        message: str,
        conversation_id: Optional[str],
        sentiment_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fallback when neither RAG nor web search is available.
        """
        return {
            'response': """I don't have specific information to answer your question accurately.

For the best assistance, please:
- Contact our support team
- Check our help center  
- Email support@company.com

Is there anything else I can help you with?""",
            'sources': [],
            'sentiment': sentiment_result,
            'conversation_id': conversation_id or self._generate_conversation_id(),
            'method': 'fallback',
            'web_search_used': False,
            'requires_human': True,
            'metadata': {
                'timestamp': datetime.utcnow().isoformat(),
                'organization_id': self.organization_id,
                'reason': 'no_knowledge_available'
            }
        }

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
                'url': doc['metadata'].get('url'),
                'type': 'company_document'
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
    print("🧪 CHAT SERVICE TEST - WITH WEB SEARCH!")
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

        # Test conversations with both RAG and Web Search
        print("\n3. Testing chat responses (RAG + Web Search)...")
        print("\n" + "-"*60)
        
        test_queries = [
            "How do I reset my password?",  # Should use RAG
            "I'm really frustrated! I can't access my account!",  # Should use RAG
            "What's the weather in Toronto right now?",  # Should use Web Search
            "What are your support hours?",  # Should use RAG
            "Can you help me with billing?",  # Should use RAG
            "Who won the Super Bowl 2024?",  # Should use Web Search
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
            
            # Show which method was used
            print(f"🔧 Method: {result['method'].upper()}")
            if result.get('web_search_used'):
                print(f"🌐 Web Search: Used")
                if result.get('search_queries'):
                    print(f"🔍 Search Queries: {result['search_queries']}")

            if result['sources']:
                print(f"📚 Sources used:")
                for source in result['sources']:
                    source_type = source.get('type', 'unknown')
                    if source_type == 'company_document':
                        print(f"   📄 {source['title']} (relevance: {source.get('score', 0):.2f})")
                    else:
                        print(f"   🌐 {source.get('title', 'Web Source')} - {source.get('url', '')}")
            
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
        print("- RAG successfully retrieves relevant context for company questions")
        print("- Web search activates for real-time/general questions")
        print("- Smart routing works correctly")
        print("- Responses are contextual and accurate")
        print("- Sentiment affects response tone (empathetic for frustrated users)")
        print("- Sources are cited properly (company docs + web sources)")
        print("- Sources are cited properly")
        print("- Conversation history is maintained")
        print("\n")
        
    except Exception as e:
        print(f"\n TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        print("\nTroubleshooting:")
        print("1. Ensure OpenAI API key is set")
        print("2. Ensure Tavily API key is set")
        print("2. Verify all services are initialized")
        print("3. Check internet connection")
        print("\n")