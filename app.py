"""
Expense Tracker Flask Application
Main application file with blueprint registration and error handling
"""

from flask import Flask, render_template, request
from flask_session import Session
from flask_wtf.csrf import CSRFProtect, generate_csrf
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import blueprints
from blueprints import auth_bp, expenses_bp, income_bp, main_bp

def create_app():
    """Application factory function"""
    app = Flask(__name__)
    
    # Configuration
    app.secret_key = os.getenv("SECRET_KEY", "dev-key-change-in-production")
    app.config["SESSION_PERMANENT"] = False
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_USE_SIGNER"] = True
    app.config["PERMANENT_SESSION_LIFETIME"] = 86400  # 24 hours
    app.config["WTF_CSRF_TIME_LIMIT"] = None
    app.config["WTF_CSRF_CHECK_DEFAULT"] = False  # Disable by default, enable selectively
    
    # Initialize extensions
    Session(app)
    CSRFProtect(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(expenses_bp, url_prefix="/expenses")
    app.register_blueprint(income_bp, url_prefix="/income")
    app.register_blueprint(main_bp)
    
    # Custom filter for currency formatting
    @app.template_filter()
    def usd(value):
        return f"${value:,.2f}"
    
    app.jinja_env.globals.update(usd=usd)
    
    # Add csrf_token to template context
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf)
    
    # Error Handlers
    @app.errorhandler(400)
    def bad_request(error):
        return render_template("error.html", code=400, message="Bad Request - Invalid input"), 400

    @app.errorhandler(404)
    def not_found(error):
        return render_template("error.html", code=404, message="Page Not Found"), 404

    @app.errorhandler(500)
    def server_error(error):
        return render_template("error.html", code=500, message="Server Error - Please try again"), 500

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("error.html", code=403, message="Access Forbidden"), 403
    db_path = "database.db"
    if not os.path.exists(db_path):
        open(db_path, "a").close()

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=os.getenv("FLASK_ENV") == "development")
