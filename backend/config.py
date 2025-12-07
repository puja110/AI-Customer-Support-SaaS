"""
Application Configuration
-------------------------
This file contains all configuration settings for the application.
Different configs for development, testing, and production.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class with common settings."""
    
    # Flask Settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = False
    TESTING = False
    
    # Database Settings
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL', 
        'sqlite:///chatbot.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Disable signal tracking (saves memory)
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = 'gpt-4-turbo-preview'  # Main chat model
    OPENAI_EMBEDDING_MODEL = 'text-embedding-3-small'  # For embeddings (1536 dims)
    
    # ChromaDB Settings
    CHROMA_PERSIST_DIRECTORY = os.getenv(
        'CHROMA_PERSIST_DIRECTORY', 
        '../data/chroma_db'
    )
    
    # AI Model Settings
    MAX_CONTEXT_LENGTH = 4000  # Maximum tokens for context
    TEMPERATURE = 0.7  # 0=focused/deterministic, 1=creative/random
    MAX_TOKENS = 500  # Maximum response length
    
    # Sentiment Analysis
    SENTIMENT_MODEL = 'distilbert-base-uncased-finetuned-sst-2-english'
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE = 20  # Requests per minute per user
    
    # JWT Settings
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour in seconds
    JWT_REFRESH_TOKEN_EXPIRES = 604800  # 7 days in seconds
    
    # Stripe Settings
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
    STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    # CORS Settings (for frontend)
    CORS_ORIGINS = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    
    # Pagination
    ITEMS_PER_PAGE = 20


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    SQLALCHEMY_ECHO = True  # Print SQL queries (helpful for debugging)


class TestingConfig(Config):
    """Testing environment configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # In-memory database for tests
    WTF_CSRF_ENABLED = False  # Disable CSRF for testing


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    # In production, all sensitive values MUST come from environment variables
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    
    # Require environment variables in production
    @classmethod
    def init_app(cls, app):
        """Additional production initialization."""
        # Ensure critical env vars are set
        required_vars = [
            'SECRET_KEY',
            'OPENAI_API_KEY',
            'STRIPE_SECRET_KEY',
            'DATABASE_URL'
        ]
        
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")


# Configuration dictionary - use this to load the right config
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(config_name=None):
    """
    Get configuration object based on environment.
    
    Args:
        config_name: Name of config ('development', 'production', etc.)
                    If None, uses FLASK_ENV environment variable
    
    Returns:
        Configuration class
    """
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    return config.get(config_name, config['default'])
