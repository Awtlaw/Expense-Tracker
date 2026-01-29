from flask import Blueprint, render_template, request, redirect, session, flash, url_for, Response
from datetime import datetime, timedelta
from io import BytesIO
from fpdf import FPDF
from helpers import validate_password, sanitize_text
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, User, Expense, Income, Budget
from sqlalchemy import func

main_bp = Blueprint('main', __name__)

@main_bp.route("/")
def index():
    return render_template("landing.html", current_year=datetime.now().year)

@main_bp.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]

    try:
        income_total = db.session.query(func.sum(Income.amount)).filter_by(user_id=user_id).scalar() or 0
        expense_total = db.session.query(func.sum(Expense.amount)).filter_by(user_id=user_id).scalar() or 0
        balance = income_total - expense_total

        current_month = datetime.now().strftime("%Y-%m")
        income_month = db.session.query(func.sum(Income.amount)).filter_by(user_id=user_id).filter(
            func.strftime('%Y-%m', Income.date) == current_month
        ).scalar() or 0
        expenses_month = db.session.query(func.sum(Expense.amount)).filter_by(user_id=user_id).filter(
            func.strftime('%Y-%m', Expense.date) == current_month
        ).scalar() or 0

        categories = db.session.query(Expense.category, func.sum(Expense.amount)).filter_by(user_id=user_id).group_by(Expense.category).all()
        expense_categories = [row[0] for row in categories] if categories else []
        expense_amounts = [row[1] for row in categories] if categories else []

        # Get budget data
        budgets = Budget.query.filter_by(user_id=user_id, month=current_month).all()
        budget_warnings = []
        budget_data = []
        
        # Get total monthly budget
        total_budget_limit = None
        for budget in budgets:
            if budget.category == 'TOTAL_MONTHLY':
                total_budget_limit = budget.budget_limit
                break
        
        total_budget_warning = None
        if total_budget_limit:
            if expenses_month > total_budget_limit:
                total_budget_warning = {
                    "limit": total_budget_limit,
                    "spent": expenses_month,
                    "exceeded": expenses_month - total_budget_limit
                }
        
        for budget in budgets:
            if budget.category == "TOTAL_MONTHLY":
                continue
            spent = db.session.query(func.sum(Expense.amount)).filter_by(user_id=user_id, category=budget.category).filter(
                func.strftime('%Y-%m', Expense.date) == current_month
            ).scalar() or 0
            percentage = (spent / budget.budget_limit * 100) if budget.budget_limit > 0 else 0
            
            budget_data.append({
                "category": budget.category,
                "limit": budget.budget_limit,
                "spent": spent,
                "remaining": max(0, budget.budget_limit - spent),
                "percentage": min(percentage, 100),
                "is_exceeded": spent > budget.budget_limit
            })
            
            if spent > budget.budget_limit:
                budget_warnings.append({
                    "category": budget.category,
                    "limit": budget.budget_limit,
                    "spent": spent,
                    "exceeded": spent - budget.budget_limit
                })

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
            budget_warnings=budget_warnings,
            budget_data=budget_data,
            total_budget_limit=total_budget_limit,
            total_budget_warning=total_budget_warning,
            current_year=datetime.now().year
        )
    except Exception as e:
        import traceback
        error_msg = f"Error loading dashboard: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        flash(f"Error loading dashboard: {str(e)}")
        return redirect(url_for("auth.login"))


@main_bp.route("/reports")
def reports():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    now = datetime.now()

    try:
        current_month = now.strftime("%Y-%m")
        last_month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        current_year = now.strftime("%Y")

        # Last 7 days expenses
        seven_days_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        weekly_expenses = db.session.query(func.sum(Expense.amount)).filter_by(user_id=user_id).filter(
            Expense.date >= seven_days_ago
        ).scalar() or 0

        # Current month expenses
        monthly_expenses = db.session.query(func.sum(Expense.amount)).filter_by(user_id=user_id).filter(
            func.strftime('%Y-%m', Expense.date) == current_month
        ).scalar() or 0

        # Current year expenses
        yearly_expenses = db.session.query(func.sum(Expense.amount)).filter_by(user_id=user_id).filter(
            func.strftime('%Y', Expense.date) == current_year
        ).scalar() or 0

        # Last month expenses
        last_month_expenses = db.session.query(func.sum(Expense.amount)).filter_by(user_id=user_id).filter(
            func.strftime('%Y-%m', Expense.date) == last_month
        ).scalar() or 0

        month_change = monthly_expenses - last_month_expenses

        categories = db.session.query(Expense.category, func.sum(Expense.amount)).filter_by(user_id=user_id).group_by(
            Expense.category
        ).order_by(func.sum(Expense.amount).desc()).all()

        category_labels = [row[0] for row in categories]
        category_totals = [row[1] for row in categories]
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
    except Exception as e:
        flash(f"Error loading reports: {str(e)}")
        return redirect(url_for("main.dashboard"))


@main_bp.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]

    try:
        user = User.query.get(user_id)

        total_income = db.session.query(func.sum(Income.amount)).filter_by(user_id=user_id).scalar() or 0

        total_expenses = db.session.query(func.sum(Expense.amount)).filter_by(user_id=user_id).scalar() or 0

        balance = total_income - total_expenses

        # Get total monthly budget
        current_month = datetime.now().strftime("%Y-%m")
        total_budget = Budget.query.filter_by(user_id=user_id, month=current_month, category='TOTAL_MONTHLY').first()
        total_monthly_budget = total_budget.budget_limit if total_budget else None
        
        # Get budget suggestions from last 90 days using subquery
        three_months_ago = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        
        # Subquery to get monthly totals per category
        monthly_totals = db.session.query(
            Expense.category,
            func.strftime('%Y-%m', Expense.date).label('month'),
            func.sum(Expense.amount).label('monthly_total')
        ).filter(
            Expense.user_id == user_id,
            Expense.date >= three_months_ago
        ).group_by(
            Expense.category,
            func.strftime('%Y-%m', Expense.date)
        ).subquery()
        
        # Query to get average of monthly totals
        category_data = db.session.query(
            monthly_totals.c.category,
            func.avg(monthly_totals.c.monthly_total).label('avg_spent')
        ).group_by(monthly_totals.c.category).all()
        
        budget_suggestions = []
        for category, avg_spent in category_data:
            avg_spent = avg_spent or 0
            suggested_budget = round(avg_spent * 1.15, 2)
            
            existing = Budget.query.filter_by(user_id=user_id, category=category, month=current_month).first()
            
            budget_suggestions.append({
                "category": category,
                "avg_spent": round(avg_spent, 2),
                "suggested": suggested_budget,
                "has_budget": existing is not None
            })

        return render_template(
            "profile.html",
            user=user,
            total_income=total_income,
            total_expenses=total_expenses,
            balance=balance,
            total_monthly_budget=total_monthly_budget,
            budget_suggestions=budget_suggestions,
            current_year=datetime.now().year
        )
    except Exception as e:
        flash(f"Error loading profile: {str(e)}")
        return redirect(url_for("main.dashboard"))


@main_bp.route("/change_password", methods=["POST"])
def change_password():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirmation = request.form.get("confirmation", "")

    if not current_password or not new_password or not confirmation:
        flash("All fields are required.")
        return redirect(url_for("main.profile"))

    if new_password != confirmation:
        flash("New passwords do not match.")
        return redirect(url_for("main.profile"))

    is_valid, msg = validate_password(new_password)
    if not is_valid:
        flash(msg)
        return redirect(url_for("main.profile"))

    try:
        user = User.query.get(user_id)

        if not check_password_hash(user.hash, current_password):
            flash("Current password is incorrect.")
            return redirect(url_for("main.profile"))

        user.hash = generate_password_hash(new_password)
        db.session.commit()
        flash("Password changed successfully!")
    except Exception as e:
        db.session.rollback()
        flash(f"Error changing password: {str(e)}")

    return redirect(url_for("main.profile"))


@main_bp.route("/export_pdf")
def export_pdf():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]

    try:
        expenses = Expense.query.filter_by(user_id=user_id).order_by(Expense.date.desc()).all()

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
            pdf.cell(40, 10, exp.date, 1)
            pdf.cell(50, 10, exp.category, 1)
            pdf.cell(30, 10, f"${exp.amount:,.2f}", 1)
            pdf.cell(70, 10, exp.note[:35] if exp.note else "", 1)
            pdf.ln()

        output = BytesIO()
        pdf.output(output)
        output.seek(0)

        return Response(output, mimetype="application/pdf",
                        headers={"Content-Disposition": "attachment; filename=expenses.pdf"})
    except Exception as e:
        flash(f"Error generating PDF: {str(e)}")
        return redirect(url_for("main.dashboard"))


@main_bp.route("/set_budget", methods=["POST"])
def set_budget():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    category = request.form.get("category", "").strip()
    budget_limit = request.form.get("budget_limit", "")
    
    if not category or not budget_limit:
        flash("Category and budget limit are required")
        return redirect(url_for("main.profile"))
    
    try:
        budget_limit = float(budget_limit)
        if budget_limit <= 0:
            flash("Budget limit must be greater than 0")
            return redirect(url_for("main.profile"))
        
        current_month = datetime.now().strftime("%Y-%m")
        existing = Budget.query.filter_by(user_id=user_id, category=category, month=current_month).first()
        
        if existing:
            existing.budget_limit = budget_limit
        else:
            new_budget = Budget(user_id=user_id, category=category, budget_limit=budget_limit, month=current_month)
            db.session.add(new_budget)
        
        db.session.commit()
        flash(f"Budget set for {category}: ${budget_limit:.2f}")
    except ValueError:
        flash("Invalid budget amount")
    except Exception as e:
        db.session.rollback()
        flash(f"Error setting budget: {str(e)}")
    
    return redirect(url_for("main.profile"))


@main_bp.route("/set_total_budget", methods=["POST"])
def set_total_budget():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    total_limit = request.form.get("total_budget", "")
    
    if not total_limit:
        flash("Total monthly budget is required")
        return redirect(url_for("main.profile"))
    
    try:
        total_limit = float(total_limit)
        if total_limit <= 0:
            flash("Budget limit must be greater than 0")
            return redirect(url_for("main.profile"))
        
        current_month = datetime.now().strftime("%Y-%m")
        existing = Budget.query.filter_by(user_id=user_id, category="TOTAL_MONTHLY", month=current_month).first()
        
        if existing:
            existing.budget_limit = total_limit
        else:
            new_budget = Budget(user_id=user_id, category="TOTAL_MONTHLY", budget_limit=total_limit, month=current_month)
            db.session.add(new_budget)
        
        db.session.commit()
        flash(f"Total monthly budget set to ${total_limit:.2f}")
    except ValueError:
        flash("Invalid budget amount")
    except Exception as e:
        db.session.rollback()
        flash(f"Error setting budget: {str(e)}")
    
    return redirect(url_for("main.profile"))


@main_bp.route("/set_budgets_bulk", methods=["POST"])
def set_budgets_bulk():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    current_month = datetime.now().strftime("%Y-%m")
    
    try:
        budgets = request.form
        count = 0
        
        for key, value in budgets.items():
            if key.startswith("budget_") and value:
                category = key.replace("budget_", "")
                try:
                    budget_limit = float(value)
                    if budget_limit > 0:
                        existing = Budget.query.filter_by(user_id=user_id, category=category, month=current_month).first()
                        if existing:
                            existing.budget_limit = budget_limit
                        else:
                            new_budget = Budget(user_id=user_id, category=category, budget_limit=budget_limit, month=current_month)
                            db.session.add(new_budget)
                        count += 1
                except ValueError:
                    continue
        
        db.session.commit()
        flash(f"Successfully set {count} budget(s)!")
    except Exception as e:
        db.session.rollback()
        flash(f"Error setting budgets: {str(e)}")
    
    return redirect(url_for("main.profile"))


@main_bp.route("/get_budgets")
def get_budgets():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    current_month = datetime.now().strftime("%Y-%m")
    
    try:
        budgets = Budget.query.filter_by(user_id=user_id, month=current_month).all()
        budget_list = [{"category": b.category, "budget_limit": b.budget_limit} for b in budgets]
        return {"budgets": budget_list}
    except Exception as e:
        flash(f"Error loading budgets: {str(e)}")
        return {"budgets": []}


@main_bp.route("/get_budget_suggestions")
def get_budget_suggestions():
    if "user_id" not in session:
        return {"suggestions": []}

    user_id = session["user_id"]
    
    try:
        three_months_ago = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        
        # Subquery to get monthly totals per category
        monthly_totals = db.session.query(
            Expense.category,
            func.strftime('%Y-%m', Expense.date).label('month'),
            func.sum(Expense.amount).label('monthly_total')
        ).filter(
            Expense.user_id == user_id,
            Expense.date >= three_months_ago
        ).group_by(
            Expense.category,
            func.strftime('%Y-%m', Expense.date)
        ).subquery()
        
        # Query to get average of monthly totals
        category_data = db.session.query(
            monthly_totals.c.category,
            func.avg(monthly_totals.c.monthly_total).label('avg_spent')
        ).group_by(monthly_totals.c.category).all()
        
        suggestions = []
        for category, avg_spent in category_data:
            avg_spent = avg_spent or 0
            suggested_budget = round(avg_spent * 1.15, 2)
            
            existing = Budget.query.filter_by(user_id=user_id, category=category, month=datetime.now().strftime("%Y-%m")).first()
            
            suggestions.append({
                "category": category,
                "avg_spent": round(avg_spent, 2),
                "suggested": suggested_budget,
                "has_budget": existing is not None
            })
        
        return {"suggestions": suggestions}
    except Exception as e:
        return {"suggestions": [], "error": str(e)}


@main_bp.route("/budgets")
def budgets_page():
    """Display all per-category budgets for the current month"""
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    
    user_id = session["user_id"]
    current_month = datetime.now().strftime("%Y-%m")
    
    try:
        budgets = Budget.query.filter_by(user_id=user_id, month=current_month).filter(
            Budget.category != 'TOTAL_MONTHLY'
        ).order_by(Budget.category).all()
        
        budget_data = []
        for budget in budgets:
            spent = db.session.query(func.sum(Expense.amount)).filter_by(user_id=user_id, category=budget.category).filter(
                func.strftime('%Y-%m', Expense.date) == current_month
            ).scalar() or 0
            
            budget_data.append({
                "id": budget.id,
                "category": budget.category,
                "limit": budget.budget_limit,
                "spent": spent,
                "remaining": max(0, budget.budget_limit - spent),
                "percentage": min((spent / budget.budget_limit * 100) if budget.budget_limit > 0 else 0, 100),
                "is_exceeded": spent > budget.budget_limit
            })
        
        return render_template(
            "budgets.html",
            budget_data=budget_data,
            current_month=current_month,
            current_year=datetime.now().year
        )
    except Exception as e:
        flash(f"Error loading budgets: {str(e)}")
        return redirect(url_for("main.dashboard"))


@main_bp.route("/delete_budget/<int:budget_id>", methods=["POST"])
def delete_budget(budget_id):
    """Delete a budget"""
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    
    user_id = session["user_id"]
    
    try:
        budget = Budget.query.get(budget_id)
        if not budget or budget.user_id != user_id:
            flash("Budget not found")
            return redirect(url_for("main.budgets_page"))
        
        db.session.delete(budget)
        db.session.commit()
        flash("Budget deleted successfully")
        return redirect(url_for("main.budgets_page"))
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting budget: {str(e)}")
        return redirect(url_for("main.budgets_page"))