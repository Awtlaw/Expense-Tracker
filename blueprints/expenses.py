from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from datetime import datetime
from cs50 import SQL
from helpers import validate_amount, validate_date, validate_category, sanitize_text
import os

db = SQL(os.getenv("DATABASE_URL", "sqlite:///database.db"))

expenses_bp = Blueprint('expenses', __name__)

@expenses_bp.route("/add_expense", methods=["POST"])
def add_expense():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    amounts = request.form.getlist("amount[]")
    categories = request.form.getlist("category[]")
    dates = request.form.getlist("date[]")
    notes = request.form.getlist("note[]")

    error_count = 0
    for amt, cat, dt, note in zip(amounts, categories, dates, notes):
        is_valid, amount = validate_amount(amt)
        if not is_valid:
            flash(f"Invalid amount: {amount}")
            error_count += 1
            continue

        is_valid, msg = validate_date(dt)
        if not is_valid:
            flash(msg)
            error_count += 1
            continue

        is_valid, msg = validate_category(cat)
        if not is_valid:
            flash(msg)
            error_count += 1
            continue

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
    
    return redirect(url_for("main.dashboard"))


@expenses_bp.route("/expense_history")
def expense_history():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    category = request.args.get("category", "")
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    page = int(request.args.get("page", 1))
    per_page = 10

    sql_query = "SELECT * FROM expenses WHERE user_id = ?"
    params = [user_id]

    if category:
        sql_query += " AND category = ?"
        params.append(category)
    if start_date:
        sql_query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        sql_query += " AND date <= ?"
        params.append(end_date)

    total_expenses = db.execute("SELECT COUNT(*) AS count FROM (" + sql_query + ")", *params)[0]["count"]
    total_pages = (total_expenses + per_page - 1) // per_page

    sql_query += " ORDER BY date DESC LIMIT ? OFFSET ?"
    params.extend([per_page, (page - 1) * per_page])

    expenses = db.execute(sql_query, *params)
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


@expenses_bp.route("/edit_expense/<int:expense_id>", methods=["GET", "POST"])
def edit_expense(expense_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    expense = db.execute("SELECT * FROM expenses WHERE id = ? AND user_id = ?", expense_id, session["user_id"])
    if not expense:
        flash("Expense not found.")
        return redirect(url_for("expenses.expense_history"))
    expense = expense[0]

    if request.method == "POST":
        is_valid, amount = validate_amount(request.form.get("amount"))
        if not is_valid:
            flash(f"Invalid amount: {amount}")
            return redirect(url_for("expenses.edit_expense", expense_id=expense_id))

        category = request.form.get("category")
        date = request.form.get("date")
        note = sanitize_text(request.form.get("note", ""))

        try:
            db.execute(
                "UPDATE expenses SET amount = ?, category = ?, date = ?, note = ? WHERE id = ?",
                amount, category, date, note, expense_id
            )
            flash("Expense updated successfully.")
        except Exception as e:
            flash(f"Error updating expense: {str(e)}")

        return redirect(url_for("expenses.expense_history"))

    return render_template("edit_expense.html", expense=expense, current_year=datetime.now().year)


@expenses_bp.route("/delete_expense/<int:expense_id>")
def delete_expense(expense_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    try:
        db.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", expense_id, session["user_id"])
        flash("Expense deleted successfully.")
    except Exception as e:
        flash(f"Error deleting expense: {str(e)}")

    return redirect(url_for("expenses.expense_history"))
