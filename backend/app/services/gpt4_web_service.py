"""
GPT-4 Web Search Service
------------------------
Combines GPT-4 with Tavily web search for real-time information.
Automatically decides when to search the web vs use existing knowledge.
"""

from tavily import TavilyClient
import openai
import os
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class GPT4WebService:
    """
    GPT-4 with intelligent web search integration.
    
    Features:
    - Automatic search decision making
    - Multi-step reasoning
    - Source attribution
    - Context-aware responses
    """
    
    def __init__(self):
        """Initialize GPT-4 and Tavily clients."""
        # OpenAI client
        self.openai_client = openai.OpenAI(
            api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Tavily client
        self.tavily = TavilyClient(
            api_key=os.getenv('TAVILY_API_KEY')
        )
        
        # Configuration
        self.model = "gpt-4"  # Can also use "gpt-4-turbo-preview"
        self.max_search_results = 5
        self.search_depth = "advanced"  # or "basic" for faster searches
        
        # System prompt for search decisions
        self.search_decision_prompt = """You are a search query analyzer.
Determine if the user's question requires real-time web search.

REQUIRES WEB SEARCH:
- Current events, news, weather, sports scores
- Stock prices, cryptocurrency, market data
- Recent information (today, this week, this month)
- Specific people, companies, products (that may have recent updates)
- YouTube videos, channels, creators
- "What's happening", "latest", "current", "now"

DOES NOT REQUIRE SEARCH:
- General knowledge (historical facts, scientific concepts)
- Math problems, coding questions
- Theoretical explanations
- Personal advice
- Company-specific questions (will be handled by RAG)

Respond ONLY in this exact format:
SEARCH: yes/no
QUERY: [optimized search query if yes, otherwise "none"]
REASON: [brief explanation]"""
    
    def chat_with_web_search(
        self,
        message: str,
        conversation_history: Optional[List[Dict]] = None,
        auto_search: bool = True,
        force_search: bool = False
    ) -> Dict:
        """
        Chat with GPT-4, automatically using web search when needed.
        
        Args:
            message: User's question
            conversation_history: Previous conversation messages
            auto_search: Let GPT-4 decide if search is needed
            force_search: Force web search regardless
        
        Returns:
            {
                "response": "AI's answer",
                "sources": [{"title": "...", "url": "...", "snippet": "..."}],
                "web_search_used": bool,
                "search_queries": ["query1"],
                "confidence": 0.95,
                "method": "web_search" or "knowledge"
            }
        """
        try:
            # Initialize
            conversation_history = conversation_history or []
            
            # Step 1: Decide if web search is needed
            if force_search:
                should_search = True
                search_query = message
                search_reason = "Forced search"
            elif auto_search:
                should_search, search_query, search_reason = self._should_search_web(message)
            else:
                should_search = False
                search_query = None
                search_reason = "Auto-search disabled"
            
            print(f"🔍 Search decision: {should_search} | Query: {search_query} | Reason: {search_reason}")
            
            # Step 2: Execute based on decision
            if should_search and search_query:
                return self._answer_with_web_search(
                    message=message,
                    search_query=search_query,
                    conversation_history=conversation_history
                )
            else:
                return self._answer_without_web_search(
                    message=message,
                    conversation_history=conversation_history
                )
                
        except Exception as e:
            print(f"❌ Error in chat_with_web_search: {e}")
            return {
                "response": f"I encountered an error: {str(e)}. Please try again.",
                "sources": [],
                "web_search_used": False,
                "search_queries": [],
                "error": str(e)
            }
    
    def _should_search_web(self, message: str) -> Tuple[bool, Optional[str], str]:
        """
        Use GPT-4 to intelligently decide if web search is needed.
        
        Returns:
            (should_search, search_query, reason)
        """
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": self.search_decision_prompt
                    },
                    {
                        "role": "user",
                        "content": f"Question: {message}"
                    }
                ],
                temperature=0.3,
                max_tokens=150
            )
            
            decision_text = response.choices[0].message.content.strip()
            
            # Parse the response
            should_search = False
            search_query = None
            reason = ""
            
            lines = decision_text.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('SEARCH:'):
                    should_search = 'yes' in line.lower()
                elif line.startswith('QUERY:'):
                    query_text = line.replace('QUERY:', '').strip()
                    if query_text.lower() != 'none':
                        search_query = query_text
                elif line.startswith('REASON:'):
                    reason = line.replace('REASON:', '').strip()
            
            return (should_search, search_query, reason)
            
        except Exception as e:
            print(f"⚠️ Error in search decision: {e}")
            # Fallback: use simple keyword detection
            return self._simple_search_detection(message)
    
    def _simple_search_detection(self, message: str) -> Tuple[bool, Optional[str], str]:
        """Fallback: Simple keyword-based search detection."""
        message_lower = message.lower()
        
        # Keywords that indicate real-time info needed
        real_time_keywords = [
            'current', 'now', 'today', 'latest', 'recent',
            'weather', 'temperature', 'forecast',
            'stock', 'price', 'cryptocurrency',
            'news', 'breaking', 'happened',
            'who won', 'score', 'result',
            'youtube', 'video', 'channel'
        ]
        
        needs_search = any(keyword in message_lower for keyword in real_time_keywords)
        
        if needs_search:
            return (True, message, "Keyword detection")
        else:
            return (False, None, "No real-time keywords detected")
    
    def _answer_with_web_search(
        self,
        message: str,
        search_query: str,
        conversation_history: List[Dict]
    ) -> Dict:
        """Execute web search and generate answer with results."""
        
        # Step 1: Search the web with Tavily
        print(f"🌐 Searching web for: {search_query}")
        
        search_results = self.tavily.search(
            query=search_query,
            search_depth=self.search_depth,
            max_results=self.max_search_results,
            include_answer=True,  # Get Tavily's AI-generated summary
            include_images=False,
            include_raw_content=False
        )
        
        # Step 2: Build context from search results
        context = self._build_search_context(search_results)
        
        # Step 3: Generate comprehensive answer with GPT-4
        response_text = self._generate_with_search_context(
            message=message,
            context=context,
            tavily_answer=search_results.get('answer', ''),
            conversation_history=conversation_history
        )
        
        # Step 4: Extract and format sources
        sources = self._extract_sources(search_results)
        
        return {
            "response": response_text,
            "sources": sources,
            "web_search_used": True,
            "search_queries": [search_query],
            "method": "web_search",
            "tavily_summary": search_results.get('answer', ''),
            "search_depth": self.search_depth,
            "timestamp": datetime.now().isoformat()
        }
    
    def _build_search_context(self, search_results: Dict) -> str:
        """Build formatted context from Tavily search results."""
        
        context = "=== WEB SEARCH RESULTS ===\n\n"
        
        results = search_results.get('results', [])
        
        if not results:
            context += "No results found.\n"
            return context
        
        for i, result in enumerate(results, 1):
            context += f"[{i}] {result.get('title', 'Untitled')}\n"
            context += f"Source: {result.get('url', 'Unknown')}\n"
            context += f"Content: {result.get('content', 'No content available')}\n"
            
            # Add score if available
            if 'score' in result:
                context += f"Relevance: {result['score']:.2f}\n"
            
            context += "\n"
        
        # Add Tavily's AI summary if available
        if search_results.get('answer'):
            context += f"=== TAVILY AI SUMMARY ===\n{search_results['answer']}\n\n"
        
        return context
    
    def _generate_with_search_context(
        self,
        message: str,
        context: str,
        tavily_answer: str,
        conversation_history: List[Dict]
    ) -> str:
        """Generate answer using GPT-4 with search context."""
        
        # Build messages
        messages = []
        
        # System message with search context
        system_content = f"""You are a helpful AI assistant with access to real-time web search.

Use the following web search results to answer the user's question accurately.
Always cite sources using [1], [2], [3], etc. matching the search result numbers.

{context}

Guidelines:
- Synthesize information from multiple sources
- Always cite which source(s) you're using
- If sources conflict, mention both perspectives
- Be factual and accurate
- Use natural, conversational language
- If search results don't answer the question, say so honestly"""

        messages.append({
            "role": "system",
            "content": system_content
        })
        
        # Add conversation history
        for msg in conversation_history[-6:]:  # Last 6 messages for context
            messages.append(msg)
        
        # Add current question
        messages.append({
            "role": "user",
            "content": message
        })
        
        # Generate response
        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        return response.choices[0].message.content
    
    def _answer_without_web_search(
        self,
        message: str,
        conversation_history: List[Dict]
    ) -> Dict:
        """Generate answer using GPT-4's existing knowledge."""
        
        messages = []
        
        # System message
        messages.append({
            "role": "system",
            "content": """You are a helpful AI assistant.
Answer based on your training knowledge.
If you're not certain, acknowledge uncertainty.
If the question requires real-time information you don't have, suggest that the user may want current information."""
        })
        
        # Add conversation history
        for msg in conversation_history[-6:]:
            messages.append(msg)
        
        # Add current question
        messages.append({
            "role": "user",
            "content": message
        })
        
        # Generate response
        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        return {
            "response": response.choices[0].message.content,
            "sources": [],
            "web_search_used": False,
            "search_queries": [],
            "method": "knowledge_only",
            "timestamp": datetime.now().isoformat()
        }
    
    def _extract_sources(self, search_results: Dict) -> List[Dict]:
        """Extract and format source citations."""
        sources = []
        
        for i, result in enumerate(search_results.get('results', []), 1):
            sources.append({
                "index": i,
                "title": result.get('title', 'Untitled'),
                "url": result.get('url', ''),
                "snippet": result.get('content', '')[:200] + '...' if result.get('content') else '',
                "score": result.get('score', 0)
            })
        
        return sources
    
    def search_youtube(self, query: str) -> Dict:
        """
        Specialized YouTube search (requires additional setup).
        For now, uses general web search with YouTube filter.
        """
        youtube_query = f"{query} site:youtube.com"
        
        return self.tavily.search(
            query=youtube_query,
            search_depth="basic",
            max_results=5
        )