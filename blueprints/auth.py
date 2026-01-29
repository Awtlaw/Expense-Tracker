from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from helpers import validate_username, validate_email_address, validate_password
from cs50 import SQL
import os

# Initialize database
db = SQL(os.getenv("DATABASE_URL", "sqlite:///database.db"))

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password required")
            return redirect(url_for("auth.login"))

        try:
            user = db.execute("SELECT * FROM users WHERE username = ?", username)

            if not user or not check_password_hash(user[0]["hash"], password):
                flash("Invalid username or password")
                return redirect(url_for("auth.login"))
            
            # Clear session after successful auth check
            session.clear()
            session["user_id"] = user[0]["id"]
            return redirect(url_for("main.dashboard"))
        except Exception as e:
            flash("An error occurred during login")
            return redirect(url_for("auth.login"))
    
    return render_template("login.html", current_year=datetime.now().year)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirmation = request.form.get("confirmation", "")

        # Validate username
        is_valid, msg = validate_username(username)
        if not is_valid:
            flash(msg)
            return redirect(url_for("auth.register"))

        # Validate email
        is_valid, msg = validate_email_address(email)
        if not is_valid:
            flash(f"Invalid email: {msg}")
            return redirect(url_for("auth.register"))

        # Validate password
        is_valid, msg = validate_password(password)
        if not is_valid:
            flash(msg)
            return redirect(url_for("auth.register"))

        # Check password match
        if password != confirmation:
            flash("Passwords do not match")
            return redirect(url_for("auth.register"))

        # Hash the password
        hash_pw = generate_password_hash(password)

        # Insert into database
        try:
            db.execute("INSERT INTO users (username, email, hash) VALUES (?, ?, ?)", 
                      username, email, hash_pw)
        except Exception as e:
            flash("Username or email already exists")
            return redirect(url_for("auth.register"))

        # Log in the new user
        user = db.execute("SELECT id FROM users WHERE username = ?", username)
        session["user_id"] = user[0]["id"]

        return redirect(url_for("main.dashboard"))

    return render_template("register.html", current_year=datetime.now().year)


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
