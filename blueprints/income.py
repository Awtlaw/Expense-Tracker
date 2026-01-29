from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from datetime import datetime
from models import db, Income
from helpers import validate_amount, validate_date, sanitize_text

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
            income = Income(user_id=session["user_id"], amount=amount, date=date, source=source)
            db.session.add(income)
            db.session.commit()
            flash("Income added successfully!")
        except Exception as e:
            db.session.rollback()
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

    query = Income.query.filter_by(user_id=user_id)

    if start_date:
        query = query.filter(Income.date >= start_date)
    if end_date:
        query = query.filter(Income.date <= end_date)

    total_rows = query.count()
    total_pages = (total_rows + per_page - 1) // per_page

    income = query.order_by(Income.date.desc()).limit(per_page).offset((page - 1) * per_page).all()

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
        income_record = Income.query.filter_by(id=income_id, user_id=session["user_id"]).first()
        if income_record:
            db.session.delete(income_record)
            db.session.commit()
            flash("Income deleted successfully.")
        else:
            flash("Income not found.")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting income: {str(e)}")

    return redirect(url_for("income.income_history"))
