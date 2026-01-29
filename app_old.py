from helpers import (validate_username, validate_email_address, validate_password, 
                     validate_amount, validate_date, validate_category, sanitize_text)





app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-key-change-in-production")

# Configure CSRF Protection
csrf = CSRFProtect(app)

# Configure session
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Database
db = SQL(os.getenv("DATABASE_URL", "sqlite:///database.db"))

# Custom filter for currency formatting


@app.template_filter()
def usd(value):
    return f"${value:,.2f}"

# Root route
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

# Dashboard


@app.route("/dashboard")
def dashboard():
    print("Session contents:", dict(session))
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # Get current balance
    income_total = db.execute("SELECT SUM(amount) AS total FROM income WHERE user_id = ?", user_id)[0]["total"] or 0
    expense_total = db.execute("SELECT SUM(amount) AS total FROM expenses WHERE user_id = ?", user_id)[0]["total"] or 0
    balance = income_total - expense_total

    # Monthly summaries
    current_month = datetime.now().strftime("%Y-%m")
    income_month = db.execute("SELECT SUM(amount) AS total FROM income WHERE user_id = ? AND strftime('%Y-%m', date) = ?", user_id, current_month)[0]["total"] or 0
    expenses_month = db.execute("SELECT SUM(amount) AS total FROM expenses WHERE user_id = ? AND strftime('%Y-%m', date) = ?", user_id, current_month)[0]["total"] or 0

    # Expenses by category
    categories = db.execute("SELECT category, SUM(amount) AS total FROM expenses WHERE user_id = ? GROUP BY category", user_id)
    expense_categories = [row["category"] for row in categories]
    expense_amounts = [row["total"] for row in categories]

    # Sample monthly data for charts (simplified)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    income_data = [1000, 1200, 1500, 1300, 1100, 1600]
    expenses_data = [500, 700, 800, 600, 500, 900]

    return render_template(
        "dashboard.html",
        balance=balance,
        income_month=income_month,
        expenses_month=expenses_month,
        expense_categories=expense_categories,
        expense_amounts=expense_amounts,
        months=months,
        income_data=income_data,
        expenses_data=expenses_data,
        current_year=datetime.now().year
    )

# Add Income
@app.route("/add_income", methods=["GET", "POST"])
def add_income():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        amount = float(request.form.get("amount"))
        date = request.form.get("date")
        source = request.form.get("source")
        db.execute("INSERT INTO income (user_id, amount, date, source) VALUES (?, ?, ?, ?)",
                   session["user_id"], amount, date, source)
        flash("Income added successfully!")
        return redirect(url_for("dashboard"))

    today = datetime.now().strftime("%Y-%m-%d")
    return render_template("add_income.html", today=today, current_year=datetime.now().year)
@app.route("/add_expense", methods=["POST"])
def add_expense():
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Get lists of inputs
    amounts = request.form.getlist("amount[]")
    categories = request.form.getlist("category[]")
    dates = request.form.getlist("date[]")
    notes = request.form.getlist("note[]")

    # Validate and insert each expense
    error_count = 0
    for amt, cat, dt, note in zip(amounts, categories, dates, notes):
        # Validate amount
        is_valid, amount = validate_amount(amt)
        if not is_valid:
            flash(f"Invalid amount: {amount}")
            error_count += 1
            continue

        # Validate date
        is_valid, msg = validate_date(dt)
        if not is_valid:
            flash(msg)
            error_count += 1
            continue

        # Validate category
        is_valid, msg = validate_category(cat)
        if not is_valid:
            flash(msg)
            error_count += 1
            continue

        # Sanitize note
        note = sanitize_text(note)

        try:
            db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, note) VALUES (?, ?, ?, ?, ?)",
                session["user_id"], amount, cat, dt, note
            )
        except Exception as e:
            flash(f"Error adding expense: {str(e)}")
            error_count += 1

    success_count = len(amounts) - error_count
    if success_count > 0:
        flash(f"{success_count} expense(s) added successfully!")
    
    return redirect(url_for("dashboard"))

# Register as a global for function-style usage in templates
app.jinja_env.globals.update(usd=usd)

# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()  # Clear previous session

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Look for the user in the database
        user = db.execute("SELECT * FROM users WHERE username = ?", username)

        if not user or not check_password_hash(user[0]["hash"], password):
            flash("Invalid username or password")
            return redirect(url_for("login"))

        # Log in the user
        session["user_id"] = user[0]["id"]

        return redirect(url_for("dashboard"))

    # GET request: show login form
    return render_template("login.html", current_year=datetime.now().year)


# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# Register
@app.route("/register", methods=["GET", "POST"])
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
            return redirect(url_for("register"))

        # Validate email
        is_valid, msg = validate_email_address(email)
        if not is_valid:
            flash(f"Invalid email: {msg}")
            return redirect(url_for("register"))

        # Validate password
        is_valid, msg = validate_password(password)
        if not is_valid:
            flash(msg)
            return redirect(url_for("register"))

        # Check password match
        if password != confirmation:
            flash("Passwords do not match")
            return redirect(url_for("register"))

        # Hash the password
        hash_pw = generate_password_hash(password)

        # Insert into database
        try:
            db.execute("INSERT INTO users (username, email, hash) VALUES (?, ?, ?)", 
                      username, email, hash_pw)
        except Exception as e:
            flash("Username or email already exists")
            return redirect(url_for("register"))

        # Log in the new user
        user = db.execute("SELECT id FROM users WHERE username = ?", username)
        session["user_id"] = user[0]["id"]

        return redirect(url_for("dashboard"))

    # GET request: show registration form
    return render_template("register.html", current_year=datetime.now().year)

@app.route("/income_history")
def income_history():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    page = int(request.args.get("page", 1))
    per_page = 10

    sql = "SELECT * FROM income WHERE user_id = ?"
    params = [user_id]

    if start_date:
        sql += " AND date >= ?"
        params.append(start_date)
    if end_date:
        sql += " AND date <= ?"
        params.append(end_date)

    total_rows = db.execute(
        "SELECT COUNT(*) AS count FROM (" + sql + ")",
        *params
    )[0]["count"]

    total_pages = (total_rows + per_page - 1) // per_page

    sql += " ORDER BY date DESC LIMIT ? OFFSET ?"
    params.extend([per_page, (page - 1) * per_page])

    income = db.execute(sql, *params)

    return render_template(
        "income_history.html",
        income=income,
        start_date=start_date,
        end_date=end_date,
        page=page,
        total_pages=total_pages,
        current_year=datetime.now().year
    )
@app.route("/delete_income/<int:income_id>")
def delete_income(income_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    db.execute(
        "DELETE FROM income WHERE id = ? AND user_id = ?",
        income_id,
        session["user_id"]
    )

    flash("Income deleted successfully.")
    return redirect(url_for("income_history"))




@app.route("/expense_history")
def expense_history():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # Get filter parameters from query string
    category = request.args.get("category", "")
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    page = int(request.args.get("page", 1))
    per_page = 10  # expenses per page

    # Base SQL query
    sql_query = "SELECT * FROM expenses WHERE user_id = ?"
    params = [user_id]

    # Apply filters
    if category:
        sql_query += " AND category = ?"
        params.append(category)
    if start_date:
        sql_query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        sql_query += " AND date <= ?"
        params.append(end_date)

    # Count total filtered rows for pagination
    total_expenses = db.execute("SELECT COUNT(*) AS count FROM (" + sql_query + ")", *params)[0]["count"]
    total_pages = (total_expenses + per_page - 1) // per_page

    # Add ordering and pagination
    sql_query += " ORDER BY date DESC LIMIT ? OFFSET ?"
    params.extend([per_page, (page - 1) * per_page])

    expenses = db.execute(sql_query, *params)

    # Fetch unique categories for the filter dropdown
    categories = [row["category"] for row in db.execute("SELECT DISTINCT category FROM expenses WHERE user_id = ?", user_id)]

    return render_template(
        "expense_history.html",
        expenses=expenses,
        categories=categories,
        current_category=category,
        start_date=start_date,
        end_date=end_date,
        page=page,
        total_pages=total_pages,
        current_year=datetime.now().year
    )
@app.route("/edit_expense/<int:expense_id>", methods=["GET", "POST"])
def edit_expense(expense_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    expense = db.execute("SELECT * FROM expenses WHERE id = ? AND user_id = ?", expense_id, session["user_id"])
    if not expense:
        flash("Expense not found.")
        return redirect(url_for("expense_history"))
    expense = expense[0]

    if request.method == "POST":
        amount = float(request.form.get("amount"))
        category = request.form.get("category")
        date = request.form.get("date")
        note = request.form.get("note")

        db.execute(
            "UPDATE expenses SET amount = ?, category = ?, date = ?, note = ? WHERE id = ?",
            amount, category, date, note, expense_id
        )
        flash("Expense updated successfully.")
        return redirect(url_for("expense_history"))

    return render_template("edit_expense.html", expense=expense, current_year=datetime.now().year)


@app.route("/delete_expense/<int:expense_id>")
def delete_expense(expense_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    db.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", expense_id, session["user_id"])
    flash("Expense deleted successfully.")
    return redirect(url_for("expense_history"))


@app.route("/reports")
def reports():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    now = datetime.now()

    current_month = now.strftime("%Y-%m")
    last_month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    current_year = now.strftime("%Y")

    # ---------- AGGREGATES ----------
    weekly_expenses = db.execute(
        "SELECT SUM(amount) AS total FROM expenses "
        "WHERE user_id = ? AND date >= date('now','-7 days')",
        user_id
    )[0]["total"] or 0

    monthly_expenses = db.execute(
        "SELECT SUM(amount) AS total FROM expenses "
        "WHERE user_id = ? AND strftime('%Y-%m', date) = ?",
        user_id, current_month
    )[0]["total"] or 0

    yearly_expenses = db.execute(
        "SELECT SUM(amount) AS total FROM expenses "
        "WHERE user_id = ? AND strftime('%Y', date) = ?",
        user_id, current_year
    )[0]["total"] or 0

    # ---------- COMPARISON ----------
    last_month_expenses = db.execute(
        "SELECT SUM(amount) AS total FROM expenses "
        "WHERE user_id = ? AND strftime('%Y-%m', date) = ?",
        user_id, last_month
    )[0]["total"] or 0

    month_change = monthly_expenses - last_month_expenses

    # ---------- CATEGORY BREAKDOWN ----------
    categories = db.execute(
        "SELECT category, SUM(amount) AS total "
        "FROM expenses WHERE user_id = ? "
        "GROUP BY category ORDER BY total DESC",
        user_id
    )

    category_labels = [row["category"] for row in categories]
    category_totals = [row["total"] for row in categories]

    top_category = category_labels[0] if category_labels else "N/A"

    return render_template(
        "reports.html",
        weekly_expenses=weekly_expenses,
        monthly_expenses=monthly_expenses,
        yearly_expenses=yearly_expenses,
        last_month_expenses=last_month_expenses,
        month_change=month_change,
        top_category=top_category,
        category_labels=category_labels,
        category_totals=category_totals,
        current_year=current_year
    )



@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    user = db.execute(
        "SELECT username, email, created_at FROM users WHERE id = ?",
        user_id
    )[0]

    total_income = db.execute(
        "SELECT SUM(amount) AS total FROM income WHERE user_id = ?",
        user_id
    )[0]["total"] or 0

    total_expenses = db.execute(
        "SELECT SUM(amount) AS total FROM expenses WHERE user_id = ?",
        user_id
    )[0]["total"] or 0

    balance = total_income - total_expenses

    return render_template(
        "profile.html",
        user=user,
        total_income=total_income,
        total_expenses=total_expenses,
        balance=balance,
        current_year=datetime.now().year
    )

@app.route("/change_password", methods=["POST"])
def change_password():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    current_password = request.form.get("current_password")
    new_password = request.form.get("new_password")
    confirmation = request.form.get("confirmation")

    if not current_password or not new_password or not confirmation:
        flash("All fields are required.")
        return redirect(url_for("profile"))

    if new_password != confirmation:
        flash("New passwords do not match.")
        return redirect(url_for("profile"))

    user = db.execute(
        "SELECT hash FROM users WHERE id = ?",
        user_id
    )[0]

    if not check_password_hash(user["hash"], current_password):
        flash("Current password is incorrect.")
        return redirect(url_for("profile"))

    new_hash = generate_password_hash(new_password)

    db.execute(
        "UPDATE users SET hash = ? WHERE id = ?",
        new_hash,
        user_id
    )

    flash("Password changed successfully!")
    return redirect(url_for("profile"))


@app.route("/export_csv")
def export_csv():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # Fetch all expenses
    expenses = db.execute("SELECT date, category, amount, note FROM expenses WHERE user_id = ? ORDER BY date DESC", user_id)



@app.route("/export_pdf")
def export_pdf():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # Fetch expenses
    expenses = db.execute("SELECT date, category, amount, note FROM expenses WHERE user_id = ? ORDER BY date DESC", user_id)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Expense Report", ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(40, 10, "Date", 1)
    pdf.cell(50, 10, "Category", 1)
    pdf.cell(30, 10, "Amount", 1)
    pdf.cell(70, 10, "Note", 1)
    pdf.ln()

    pdf.set_font("Arial", "", 12)
    for exp in expenses:
        pdf.cell(40, 10, exp["date"], 1)
        pdf.cell(50, 10, exp["category"], 1)
        pdf.cell(30, 10, f"${exp['amount']:,.2f}", 1)
        pdf.cell(70, 10, exp["note"][:35], 1)  # truncate notes
        pdf.ln()

    output = BytesIO()
    pdf.output(output)
    output.seek(0)

    return Response(output, mimetype="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=expenses.pdf"})






if __name__ == "__main__":
    app.run(debug=True)


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
