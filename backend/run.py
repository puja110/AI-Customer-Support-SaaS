"""
Application Entry Point
-----------------------
This is the main file to run the Flask application.
Run with: python run.py
"""

from flask import Flask, jsonify
from flask_cors import CORS
from config import get_config
import os

def create_app(config_name=None):
    """
    Application factory pattern.
    Creates and configures the Flask application.
    
    Args:
        config_name: Configuration to use ('development', 'production', etc.)
    
    Returns:
        Configured Flask app
    """
    # Create Flask app
    # app = Flask(__name__)
    app = Flask(__name__, 
            static_folder='../frontend',
            static_url_path='/static')
    
    # Load configuration
    config = get_config(config_name)
    app.config.from_object(config)
    
    # Initialize CORS (Cross-Origin Resource Sharing)
    # This allows your frontend to communicate with the backend
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",  # Allow all origins
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Type"],
            "supports_credentials": False  # Changed to False
        }
    })
    
    # Register blueprints (API routes) - we'll add these later
    # from app.api import auth_bp, chat_bp, admin_bp
    # app.register_blueprint(auth_bp, url_prefix='/api/auth')
    # app.register_blueprint(chat_bp, url_prefix='/api/chat')
    # app.register_blueprint(admin_bp, url_prefix='/api/admin')

    # Register blueprints (API routes)
    from app.api.chat import chat_bp
    from app.api.documents import documents_bp
    
    app.register_blueprint(chat_bp)
    app.register_blueprint(documents_bp)
    
    # Basic routes for testing
    @app.route('/')
    def home():
        """Home endpoint - confirms API is running."""
        return jsonify({
            'message': 'AI Support SaaS API',
            'version': '1.0.0',
            'status': 'running',
            'environment': app.config.get('ENV', 'development')
        })
    
    @app.route('/health')
    def health():
        """Health check endpoint - used by monitoring services."""
        return jsonify({
            'status': 'healthy',
            'database': 'connected',  # We'll add real DB check later
            'ai_service': 'operational'
        }), 200
    
    @app.route('/api/test')
    def test_api():
        """Test endpoint to verify API is accessible."""
        return jsonify({
            'message': 'API is working!',
            'cors_enabled': True,
            'config_loaded': True
        })
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        }), 500
    
    # Log configuration in development
    if app.debug:
        print("\n" + "="*50)
        print("Flask Application Started")
        print("="*50)
        print(f"Environment: {app.config.get('ENV', 'development')}")
        print(f"Debug Mode: {app.debug}")
        print(f"Database: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not configured')}")
        print(f"OpenAI Key: {'✓ Configured' if app.config.get('OPENAI_API_KEY') else '✗ Missing'}")
        print(f"Stripe Key: {'✓ Configured' if app.config.get('STRIPE_SECRET_KEY') else '✗ Missing'}")
        print("="*50 + "\n")
    
    return app


# Create app instance
app = create_app()


if __name__ == '__main__':
    """
    Run the application.
    This is for development only!
    In production, use: gunicorn run:app
    """
    # Get port from environment or default to 5000
    port = int(os.getenv('PORT', 5004))
    
    # Run the app
    app.run(
        host='0.0.0.0',  # Makes server accessible externally
        port=port,
        debug=True  # Enable debug mode for development
    )
