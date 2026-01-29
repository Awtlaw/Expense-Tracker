from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from helpers import validate_username, validate_email_address, validate_password
from models import db, User

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
            user = User.query.filter_by(username=username).first()

            if not user or not check_password_hash(user.hash, password):
                flash("Invalid username or password")
                return redirect(url_for("auth.login"))
            
            # Clear session after successful auth check
            session.clear()
            session["user_id"] = user.id
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

        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists")
            return redirect(url_for("auth.register"))
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash("Email already exists")
            return redirect(url_for("auth.register"))

        # Hash the password and create new user
        hash_pw = generate_password_hash(password)
        new_user = User(username=username, email=email, hash=hash_pw)
        
        try:
            db.session.add(new_user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash("Error creating account")
            return redirect(url_for("auth.register"))

        # Log in the new user
        session["user_id"] = new_user.id
        return redirect(url_for("main.dashboard"))

    return render_template("register.html", current_year=datetime.now().year)


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
