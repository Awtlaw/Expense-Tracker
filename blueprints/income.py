from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from datetime import datetime
from cs50 import SQL
from helpers import validate_amount, validate_date, sanitize_text
import os

db = SQL(os.getenv("DATABASE_URL", "sqlite:///database.db"))

income_bp = Blueprint('income', __name__)

@income_bp.route("/add_income", methods=["GET", "POST"])
def add_income():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        is_valid, amount = validate_amount(request.form.get("amount"))
        if not is_valid:
            flash(f"Invalid amount: {amount}")
            return redirect(url_for("income.add_income"))

        date = request.form.get("date")
        is_valid, msg = validate_date(date)
        if not is_valid:
            flash(msg)
            return redirect(url_for("income.add_income"))

        source = sanitize_text(request.form.get("source", ""))
        if not source:
            flash("Income source is required")
            return redirect(url_for("income.add_income"))

        try:
            db.execute("INSERT INTO income (user_id, amount, date, source) VALUES (?, ?, ?, ?)",
                       session["user_id"], amount, date, source)
            flash("Income added successfully!")
        except Exception as e:
            flash(f"Error adding income: {str(e)}")

        return redirect(url_for("main.dashboard"))

    today = datetime.now().strftime("%Y-%m-%d")
    return render_template("add_income.html", today=today, current_year=datetime.now().year)


@income_bp.route("/income_history")
def income_history():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

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

    total_rows = db.execute("SELECT COUNT(*) AS count FROM (" + sql + ")", *params)[0]["count"]
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


@income_bp.route("/delete_income/<int:income_id>")
def delete_income(income_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    try:
        db.execute("DELETE FROM income WHERE id = ? AND user_id = ?", income_id, session["user_id"])
        flash("Income deleted successfully.")
    except Exception as e:
        flash(f"Error deleting income: {str(e)}")

    return redirect(url_for("income.income_history"))
