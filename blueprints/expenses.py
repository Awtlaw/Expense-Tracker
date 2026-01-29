from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from datetime import datetime
from models import db, Expense
from helpers import validate_amount, validate_date, validate_category, sanitize_text
from sqlalchemy import func

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
            expense = Expense(user_id=session["user_id"], amount=amount, category=cat, date=dt, note=note)
            db.session.add(expense)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
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

    query = Expense.query.filter_by(user_id=user_id)

    if category:
        query = query.filter_by(category=category)
    if start_date:
        query = query.filter(Expense.date >= start_date)
    if end_date:
        query = query.filter(Expense.date <= end_date)

    total_expenses = query.count()
    total_pages = (total_expenses + per_page - 1) // per_page

    expenses = query.order_by(Expense.date.desc()).limit(per_page).offset((page - 1) * per_page).all()
    
    categories_list = [row[0] for row in db.session.query(Expense.category).filter_by(user_id=user_id).distinct().all()]

    return render_template(
        "expense_history.html",
        expenses=expenses,
        categories=categories_list,
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

    expense = Expense.query.filter_by(id=expense_id, user_id=session["user_id"]).first()
    if not expense:
        flash("Expense not found.")
        return redirect(url_for("expenses.expense_history"))

    if request.method == "POST":
        is_valid, amount = validate_amount(request.form.get("amount"))
        if not is_valid:
            flash(f"Invalid amount: {amount}")
            return redirect(url_for("expenses.edit_expense", expense_id=expense_id))

        category = request.form.get("category")
        date = request.form.get("date")
        note = sanitize_text(request.form.get("note", ""))

        try:
            expense.amount = amount
            expense.category = category
            expense.date = date
            expense.note = note
            db.session.commit()
            flash("Expense updated successfully.")
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating expense: {str(e)}")

        return redirect(url_for("expenses.expense_history"))

    return render_template("edit_expense.html", expense=expense, current_year=datetime.now().year)


@expenses_bp.route("/delete_expense/<int:expense_id>")
def delete_expense(expense_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    try:
        expense = Expense.query.filter_by(id=expense_id, user_id=session["user_id"]).first()
        if expense:
            db.session.delete(expense)
            db.session.commit()
            flash("Expense deleted successfully.")
        else:
            flash("Expense not found.")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting expense: {str(e)}")

    return redirect(url_for("expenses.expense_history"))

    return redirect(url_for("expenses.expense_history"))
