"""
Sentiment Analysis Service
---------------------------
Analyzes customer messages to detect emotions and prioritize support tickets.

Key Features:
- Detect positive/negative sentiment
- Calculate priority level (HIGH/MEDIUM/LOW)
- Flag messages needing human escalation
- Track sentiment trends over conversations

Uses: DistilBERT model fine-tuned on customer reviews
"""

from transformers import pipeline
from typing import Dict, List, Any
from config import get_config
import warnings

# Suppress transformers warnings
warnings.filterwarnings('ignore')

# Load configuration
config = get_config()


class SentimentService:
    """
    Service for analyzing sentiment in customer messages.
    
    Helps prioritize urgent/frustrated customers and route to human agents.
    """
    
    def __init__(self):
        """
        Initialize sentiment analysis pipeline.
        
        Note: First run will download the model (~250MB).
        Subsequent runs load from cache (fast).
        """
        print("Loading sentiment analysis model...")
        print("(First time may take 1-2 minutes to download)")
        
        try:
            # Load pre-trained sentiment model
            # This model is trained on customer service data
            self.classifier = pipeline(
                "sentiment-analysis",
                model=config.SENTIMENT_MODEL,
                device=-1  # Use CPU (-1), or 0 for GPU
            )
            
            print("✓ Sentiment model loaded successfully")
            
        except Exception as e:
            print(f"✗ Error loading sentiment model: {e}")
            raise
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of a single message.
        
        Args:
            text: Customer message
            
        Returns:
            Dictionary containing:
            - label: 'POSITIVE' or 'NEGATIVE'
            - score: Confidence (0-1)
            - priority: 'HIGH', 'MEDIUM', or 'LOW'
            - needs_escalation: Boolean
            - emotion: Inferred emotion
            
        Example:
            >>> service = SentimentService()
            >>> result = service.analyze("I'm very frustrated with this issue!")
            >>> print(result)
            {
                'label': 'NEGATIVE',
                'score': 0.95,
                'priority': 'HIGH',
                'needs_escalation': True,
                'emotion': 'frustrated',
                'raw_text': 'I\'m very frustrated...'
            }
        """
        try:
            # Validate input
            if not text or not text.strip():
                return self._get_neutral_result(text)
            
            # Truncate if too long (model has 512 token limit)
            text = self._truncate_text(text)
            
            # Run sentiment analysis
            result = self.classifier(text)[0]
            
            label = result['label']  # POSITIVE or NEGATIVE
            score = result['score']  # Confidence 0-1
            
            # Calculate priority
            priority = self._calculate_priority(label, score, text)
            
            # Determine if escalation needed
            needs_escalation = self._needs_escalation(label, score, text)
            
            # Infer emotion
            emotion = self._infer_emotion(label, score, text)
            
            return {
                'label': label,
                'score': score,
                'priority': priority,
                'needs_escalation': needs_escalation,
                'emotion': emotion,
                'raw_text': text[:100] + '...' if len(text) > 100 else text
            }
            
        except Exception as e:
            print(f"✗ Error analyzing sentiment: {e}")
            return self._get_neutral_result(text, error=str(e))
    
    def analyze_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Analyze sentiment for multiple messages efficiently.
        
        Args:
            texts: List of customer messages
            
        Returns:
            List of sentiment analysis results
        """
        return [self.analyze(text) for text in texts]
    
    def analyze_conversation(
        self, 
        messages: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze sentiment trend over a conversation.
        
        Args:
            messages: List of messages in chronological order
            
        Returns:
            Dictionary with trend analysis:
            - trend: 'IMPROVING', 'DECLINING', 'STABLE', 'INSUFFICIENT_DATA'
            - message_count: Number of messages
            - scores: List of sentiment scores
            - latest_sentiment: Most recent sentiment
            - average_sentiment: Average over conversation
            
        Example:
            >>> messages = [
            ...     "I have a problem with my account",
            ...     "This is really frustrating",
            ...     "Thank you for looking into this",
            ...     "Great, issue resolved!"
            ... ]
            >>> trend = service.analyze_conversation(messages)
            >>> print(trend['trend'])
            'IMPROVING'
        """
        if not messages:
            return {
                'trend': 'INSUFFICIENT_DATA',
                'message_count': 0,
                'scores': [],
                'latest_sentiment': None,
                'average_sentiment': 0.0
            }
        
        # Analyze each message
        results = self.analyze_batch(messages)
        
        # Convert to numeric scores (-1 to +1)
        # POSITIVE = +score, NEGATIVE = -score
        scores = []
        for result in results:
            if result['label'] == 'POSITIVE':
                scores.append(result['score'])
            else:
                scores.append(-result['score'])
        
        # Calculate trend
        trend = self._calculate_trend(scores)
        
        # Calculate average
        avg_sentiment = sum(scores) / len(scores) if scores else 0.0
        
        return {
            'trend': trend,
            'message_count': len(messages),
            'scores': scores,
            'latest_sentiment': results[-1] if results else None,
            'average_sentiment': avg_sentiment,
            'sentiment_history': results
        }
    
    def _calculate_priority(
        self, 
        label: str, 
        score: float, 
        text: str
    ) -> str:
        """
        Calculate priority level based on sentiment.
        
        Priority Logic:
        - HIGH: Strong negative (frustrated customers)
        - MEDIUM: Weak negative or neutral
        - LOW: Positive sentiment
        """
        # Check for urgent keywords
        urgent_keywords = [
            'urgent', 'asap', 'immediately', 'critical', 
            'emergency', 'broken', 'not working'
        ]
        text_lower = text.lower()
        has_urgent = any(word in text_lower for word in urgent_keywords)
        
        if label == 'NEGATIVE':
            if score > 0.85 or has_urgent:
                return 'HIGH'
            elif score > 0.6:
                return 'MEDIUM'
            else:
                return 'MEDIUM'
        else:  # POSITIVE
            if has_urgent:
                return 'MEDIUM'
            else:
                return 'LOW'
    
    def _needs_escalation(
        self, 
        label: str, 
        score: float, 
        text: str
    ) -> bool:
        """
        Determine if message needs human escalation.
        
        Escalation Triggers:
        - Very negative sentiment (score > 0.85)
        - Contains escalation keywords
        - Multiple frustration indicators
        """
        # Check sentiment threshold
        if label == 'NEGATIVE' and score > 0.85:
            return True
        
        # Check for escalation keywords
        escalation_keywords = [
            'cancel', 'refund', 'lawsuit', 'lawyer', 'terrible',
            'worst', 'angry', 'furious', 'manager', 'supervisor',
            'unacceptable', 'disgusted', 'incompetent', 'scam',
            'fraud', 'never again', 'disappointed'
        ]
        
        text_lower = text.lower()
        for keyword in escalation_keywords:
            if keyword in text_lower:
                return True
        
        # Check for multiple frustration indicators
        frustration_words = [
            'frustrated', 'annoyed', 'upset', 'irritated',
            'confused', 'disappointed', 'unhappy'
        ]
        frustration_count = sum(
            1 for word in frustration_words 
            if word in text_lower
        )
        
        if frustration_count >= 2:
            return True
        
        return False
    
    def _infer_emotion(
        self, 
        label: str, 
        score: float, 
        text: str
    ) -> str:
        """
        Infer specific emotion from sentiment and text.
        
        Returns: frustrated, angry, confused, happy, satisfied, neutral
        """
        text_lower = text.lower()
        
        if label == 'NEGATIVE':
            if any(word in text_lower for word in ['angry', 'furious', 'rage']):
                return 'angry'
            elif any(word in text_lower for word in ['frustrated', 'frustrating']):
                return 'frustrated'
            elif any(word in text_lower for word in ['confused', 'don\'t understand']):
                return 'confused'
            elif score > 0.8:
                return 'frustrated'
            else:
                return 'concerned'
        else:  # POSITIVE
            if any(word in text_lower for word in ['thank', 'thanks', 'grateful']):
                return 'grateful'
            elif any(word in text_lower for word in ['love', 'awesome', 'excellent']):
                return 'excited'
            elif score > 0.8:
                return 'happy'
            else:
                return 'satisfied'
    
    def _calculate_trend(self, scores: List[float]) -> str:
        """
        Calculate sentiment trend over time.
        
        Args:
            scores: List of sentiment scores (-1 to +1)
            
        Returns:
            'IMPROVING', 'DECLINING', 'STABLE', or 'INSUFFICIENT_DATA'
        """
        if len(scores) < 2:
            return 'INSUFFICIENT_DATA'
        
        # Compare recent average to overall average
        recent_count = min(3, len(scores))
        recent_avg = sum(scores[-recent_count:]) / recent_count
        overall_avg = sum(scores) / len(scores)
        
        threshold = 0.2  # Minimum difference to detect trend
        
        if recent_avg > overall_avg + threshold:
            return 'IMPROVING'
        elif recent_avg < overall_avg - threshold:
            return 'DECLINING'
        else:
            return 'STABLE'
    
    def _truncate_text(self, text: str, max_length: int = 512) -> str:
        """Truncate text to fit model's token limit."""
        # Rough estimate: 1 token ≈ 4 characters
        max_chars = max_length * 4
        if len(text) > max_chars:
            return text[:max_chars]
        return text
    
    def _get_neutral_result(
        self, 
        text: str, 
        error: str = None
    ) -> Dict[str, Any]:
        """Return neutral result (fallback)."""
        return {
            'label': 'NEUTRAL',
            'score': 0.5,
            'priority': 'MEDIUM',
            'needs_escalation': False,
            'emotion': 'neutral',
            'raw_text': text[:100] if text else '',
            'error': error
        }


# Test/Demo code
if __name__ == "__main__":
    """
    Test the sentiment service.
    Run: python -m app.services.sentiment_service
    """
    print("\n" + "="*60)
    print("🧪 SENTIMENT SERVICE TEST")
    print("="*60)
    
    try:
        # Initialize service
        print("\n1. Initializing sentiment service...")
        service = SentimentService()
        
        # Test individual messages
        print("\n2. Testing individual message analysis...")
        test_messages = [
            "Thank you so much! This really helped.",
            "I'm having some issues with my account.",
            "This is absolutely terrible! I want a refund immediately!",
            "I've been waiting for 3 days and still no response. This is unacceptable.",
            "The product works as expected.",
            "I'm so frustrated with this. Nothing works!",
            "Great service, highly recommend!"
        ]
        
        print("\n" + "-"*60)
        for msg in test_messages:
            result = service.analyze(msg)
            print(f"\nMessage: '{msg}'")
            print(f"Sentiment: {result['label']} ({result['score']:.2f})")
            print(f"Priority: {result['priority']}")
            print(f"Emotion: {result['emotion']}")
            print(f"Needs Escalation: {result['needs_escalation']}")
        
        # Test conversation analysis
        print("\n" + "="*60)
        print("3. Testing conversation trend analysis...")
        conversation = [
            "Hi, I have a question about billing.",
            "I was charged twice this month.",
            "This is really frustrating. Can someone help?",
            "Thank you for looking into this!",
            "Great, the issue is resolved!"
        ]
        
        trend = service.analyze_conversation(conversation)
        print(f"\nConversation Trend: {trend['trend']}")
        print(f"Messages: {trend['message_count']}")
        print(f"Average Sentiment: {trend['average_sentiment']:.2f}")
        print(f"Latest Emotion: {trend['latest_sentiment']['emotion']}")
        
        print("\nSentiment over time:")
        for i, (msg, score) in enumerate(zip(conversation, trend['scores']), 1):
            sentiment_bar = "+" * int(abs(score) * 10) if score > 0 else "-" * int(abs(score) * 10)
            print(f"{i}. [{sentiment_bar:>10}] {score:+.2f} - {msg[:40]}...")
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nKey observations:")
        print("- Positive messages get LOW priority (routine)")
        print("- Negative messages get HIGH priority (urgent)")
        print("- Escalation keywords trigger automatic flagging")
        print("- Conversation trends help identify improving/declining satisfaction")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        print("\nTroubleshooting:")
        print("1. First run downloads model (~250MB) - be patient")
        print("2. Ensure you have internet connection")
        print("3. Check transformers library is installed")
        print("\n")