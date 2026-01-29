# Input validation helpers
from email_validator import validate_email, EmailNotValidError
from decimal import Decimal

def validate_username(username):
    """Validate username format and length"""
    if not username or len(username) < 3 or len(username) > 50:
        return False, "Username must be between 3-50 characters"
    if not username.isalnum() and "_" not in username:
        return False, "Username can only contain letters, numbers, and underscores"
    return True, ""

def validate_email_address(email):
    """Validate email format"""
    try:
        validate_email(email)
        return True, ""
    except EmailNotValidError as e:
        return False, str(e)

def validate_password(password):
    """Validate password strength"""
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters"
    if len(password) > 128:
        return False, "Password is too long"
    return True, ""

def validate_amount(amount_str):
    """Validate monetary amount"""
    try:
        amount = float(amount_str)
        if amount <= 0:
            return False, "Amount must be greater than 0"
        if amount > 999999.99:
            return False, "Amount is too large"
        return True, amount
    except (ValueError, TypeError):
        return False, "Invalid amount format"

def validate_date(date_str):
    """Validate date format (YYYY-MM-DD)"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True, ""
    except ValueError:
        return False, "Invalid date format (use YYYY-MM-DD)"

def validate_category(category):
    """Validate expense/income category"""
    valid_categories = ["Food", "Transport", "Utilities", "Entertainment", "Healthcare", 
                       "Shopping", "Salary", "Freelance", "Investment", "Other"]
    if category not in valid_categories:
        return False, f"Invalid category. Must be one of: {', '.join(valid_categories)}"
    return True, ""

def sanitize_text(text, max_length=500):
    """Sanitize text input"""
    if not isinstance(text, str):
        return ""
    text = text.strip()
    if len(text) > max_length:
        text = text[:max_length]
    return text

from datetime import datetime
